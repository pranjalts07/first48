-- Article type from Wikidata "instance of". A page with several values gets
-- the first matching group in this order; unmatched or missing is "other".
create or replace table stg_article_types as
with priority(article_type, rank) as (
    values ('person', 1), ('film_tv', 2), ('sports_event', 3), ('place', 4), ('organization', 5)
),
matches as (
    select s.page_id, t.article_type, p.rank
    from (select page_id, unnest(instance_of) as qid from stg_snapshots) s
    join seed_article_types t using (qid)
    join priority p using (article_type)
)
select
    s.page_id,
    coalesce(arg_min(m.article_type, m.rank), 'other') as article_type,
    list_contains(s.instance_of, 'Q4167410') as is_disambiguation
from stg_snapshots s
left join matches m using (page_id)
group by s.page_id, s.instance_of;
