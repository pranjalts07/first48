-- Edit activity from t0 to the end of day 1, from the edits file of the
-- cohort the page first entered in.
create or replace table stg_edits as
select
    e.page_id,
    e.edits_d0,
    e.edits_48h,
    e.editors_48h,
    e.size_d0,
    e.size_d1
from raw_edits e
join stg_new_pages p
    on p.page_id = e.page_id
    and p.cohort_date = cast(regexp_extract(e.filename, '(\d{4}-\d{2}-\d{2})\.jsonl$', 1) as date)
    and p.dataset = e.dataset;
