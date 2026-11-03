-- One row per page: the first time it entered article space.
create or replace table stg_new_pages as
with entries as (
    select
        page_id,
        title as title_at_t0,
        strptime(t0, '%Y-%m-%dT%H:%M:%SZ') as t0,
        source,
        dataset,
        count(*) over (partition by page_id) as n_entries,
        row_number() over (partition by page_id order by t0, dataset) as entry
    from raw_new_pages
)
select
    page_id,
    title_at_t0,
    t0,
    cast(t0 as date) as cohort_date,
    source,
    dataset,
    n_entries
from entries
where entry = 1;
