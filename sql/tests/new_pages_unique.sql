select page_id from stg_new_pages group by page_id having count(*) > 1
