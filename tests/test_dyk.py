import datetime as dt

import pandas as pd

from first48 import dyk

WIKITEXT = """==Did you know...==
===2 March 2025===
*'''''00:00, 2 March 2025 (UTC)'''''
{{main page image/DYK|image=X.jpg|caption=[[Not featured]]}}
* ... that '''[[Alpha]]''' and '''''[[Beta_film|its film]]''''' were made in ''[[Gamma]]''?
===1 March 2025===
*'''''12:00, 1 March 2025 (UTC)'''''
* ... that '''[[Delta]]''' exists?
*'''''00:00, 1 March 2025 (UTC)'''''
* ... that '''[[Epsilon]]''' exists?
"""


def test_archive_gives_bold_links_per_set():
    sets = dyk.parse_archive(WIKITEXT)
    assert sets[0] == (dt.datetime(2025, 3, 2), ["Alpha", "Beta film"])
    assert [t for _, t in sets] == [["Alpha", "Beta film"], ["Delta"], ["Epsilon"]]


def test_set_is_shown_from_when_the_previous_set_left():
    rows = dyk.shown_windows(dyk.parse_archive(WIKITEXT))
    delta = next(r for r in rows if r["title"] == "Delta")
    assert (delta["shown_from"], delta["shown_until"]) == (dt.datetime(2025, 3, 1), dt.datetime(2025, 3, 1, 12))
    # The oldest set has no known start, so it is dropped.
    assert "Epsilon" not in {r["title"] for r in rows}


def test_featured_only_from_day_2_to_day_29():
    articles = pd.DataFrame({"page_id": [1, 2, 3, 4], "cohort_date": [dt.date(2025, 3, 1)] * 4})
    shown = [{"page_id": 1, "shown_from": "2025-03-02T00:00:00Z"},
             {"page_id": 2, "shown_from": "2025-03-03T12:00:00Z"},
             {"page_id": 3, "shown_from": "2025-04-05T00:00:00Z"}]
    featured = dyk.featured_after_day_1(articles, shown)
    assert featured.to_dict() == {1: False, 2: True, 3: False, 4: False}


def test_errors_are_split_and_seeds_averaged():
    preds = pd.DataFrame({"origin": 0, "page_id": [1, 2], "views_30d": [99, 99],
                          "flat_rate": [99, 9], "lightgbm_seed0": [99, 99], "lightgbm_seed1": [9, 9]})
    out = dyk.errors_by_group(preds, pd.Series({1: True}))
    assert set(out["model"]) == {"flat_rate", "lightgbm"}
    flat = out[out["model"] == "flat_rate"].set_index("featured")["median_abs_log_error"]
    assert flat[True] == 0 and flat[False] > 0
