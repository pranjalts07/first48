select page_id from fct_articles group by page_id having count(*) > 1
