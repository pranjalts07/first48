select *
from fct_articles
where creation_hour not between 0 and 23
    or weekday not between 1 and 7
    or article_type not in ('person', 'film_tv', 'sports_event', 'place', 'organization', 'other')
    or views_d0 is null
    or views_d1 is null
