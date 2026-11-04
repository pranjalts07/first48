select *
from stg_edits
where edits_d0 < 0
    or edits_d0 > edits_48h
    or editors_48h > edits_48h
    or (edits_48h > 0 and size_d1 is null)
