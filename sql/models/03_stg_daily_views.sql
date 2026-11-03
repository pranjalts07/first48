-- One row per page, fetch kind and day since t0. The pageviews API leaves
-- out some zero-view days, so a missing day counts as zero.
create or replace table stg_daily_views as
with files as (
    select
        v.page_id,
        v.dataset,
        regexp_extract(v.filename, 'views_(early|full)_', 1) as kind,
        p.cohort_date,
        v.views
    from raw_views v
    join stg_new_pages p
        on p.page_id = v.page_id
        and p.cohort_date = cast(regexp_extract(v.filename, '(\d{4}-\d{2}-\d{2})\.jsonl$', 1) as date)
        and p.dataset = v.dataset
),
days as (
    select
        page_id,
        dataset,
        kind,
        cohort_date,
        views,
        cast(unnest(range(case kind when 'full' then 30 else 2 end)) as integer) as day_index
    from files
)
select
    page_id,
    dataset,
    kind,
    day_index,
    cohort_date + day_index as view_date,
    coalesce(views[strftime(cohort_date + day_index, '%Y-%m-%d')], 0) as views
from days;
