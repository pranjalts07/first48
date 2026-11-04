select page_id
from stg_edits
group by page_id
having count(*) > 1
