-- Page state from the snapshot of the cohort the page first entered in.
create or replace table stg_snapshots as
select
    s.page_id,
    s.dataset,
    strptime(s.taken_at, '%Y-%m-%dT%H:%M:%SZ') as taken_at,
    s."exists",
    s.namespace,
    s.is_redirect,
    s.title,
    s.last_rev_id,
    s.wikidata_item,
    coalesce(s.instance_of, []) as instance_of,
    coalesce(s."exists" and s.namespace = 0 and not s.is_redirect, false) as is_article
from raw_snapshots s
join stg_new_pages p
    on p.page_id = s.page_id
    and p.cohort_date = cast(regexp_extract(s.filename, '(\d{4}-\d{2}-\d{2})\.jsonl$', 1) as date)
    and p.dataset = s.dataset
qualify row_number() over (partition by s.page_id order by s.taken_at desc) = 1;
