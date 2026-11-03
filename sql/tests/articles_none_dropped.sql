-- Every article whose cohort has a 30-day views file should reach fct_articles.
select s.page_id
from stg_snapshots s
join stg_new_pages p using (page_id)
where s.is_article
    and exists (
        select 1 from stg_daily_views v
        where v.kind = 'full' and v.dataset = p.dataset
            and v.view_date = p.cohort_date
    )
    and s.page_id not in (select page_id from fct_articles)
