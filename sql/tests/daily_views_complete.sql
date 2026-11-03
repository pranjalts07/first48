-- Every view file row expands to exactly 2 or 30 days.
select page_id, dataset, kind, count(*) as n
from stg_daily_views
group by page_id, dataset, kind
having count(*) <> case kind when 'full' then 30 else 2 end
