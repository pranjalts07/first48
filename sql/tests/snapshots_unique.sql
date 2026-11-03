select page_id from stg_snapshots group by page_id having count(*) > 1
