-- One row per article with complete 30-day views: the modeling table.
-- views_d0 and views_d1 are the only view inputs a forecast may use.
create or replace table fct_articles as
with totals as (
    select
        page_id,
        sum(views) filter (where day_index = 0) as views_d0,
        sum(views) filter (where day_index = 1) as views_d1,
        sum(views) as views_30d
    from stg_daily_views
    where kind = 'full'
    group by page_id
)
select
    p.page_id,
    p.dataset,
    p.cohort_date,
    p.t0,
    hour(p.t0) as creation_hour,
    isodow(p.t0) as weekday,
    p.source,
    s.title,
    s.title <> p.title_at_t0 as renamed,
    p.n_entries,
    s.wikidata_item,
    t.article_type,
    t.is_disambiguation,
    v.views_d0,
    v.views_d1,
    v.views_d0 + v.views_d1 as views_48h,
    v.views_30d,
    e.edits_d0,
    e.edits_48h,
    e.editors_48h,
    e.size_d0,
    e.size_d1
from stg_new_pages p
join stg_snapshots s using (page_id)
join stg_article_types t using (page_id)
join totals v using (page_id)
left join stg_edits e using (page_id)
where s.is_article;
