-- Per creation day: how many pages arrived, how many are articles, and
-- typical early and 30-day views. Used for data checks and drift plots.
create or replace table cohort_summary as
select
    p.dataset,
    p.cohort_date,
    count(*) as new_pages,
    count(*) filter (where s.is_article) as articles,
    count(a.page_id) as articles_with_views,
    median(a.views_48h) as median_views_48h,
    median(a.views_30d) as median_views_30d
from stg_new_pages p
left join stg_snapshots s using (page_id)
left join fct_articles a using (page_id)
group by p.dataset, p.cohort_date
order by p.dataset, p.cohort_date;
