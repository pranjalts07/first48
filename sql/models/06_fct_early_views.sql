-- Day 0 and day 1 views for live articles, fetched before their 30-day
-- outcome exists. Shadow-mode predictions are made from this table.
create or replace table fct_early_views as
select
    p.page_id,
    p.cohort_date,
    p.t0,
    hour(p.t0) as creation_hour,
    isodow(p.t0) as weekday,
    p.source,
    s.title,
    t.article_type,
    sum(v.views) filter (where v.day_index = 0) as views_d0,
    sum(v.views) filter (where v.day_index = 1) as views_d1
from stg_daily_views v
join stg_new_pages p using (page_id)
join stg_snapshots s using (page_id)
join stg_article_types t using (page_id)
where v.kind = 'early' and s.is_article
group by all;
