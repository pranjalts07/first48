import datetime as dt

from first48.checks import check_snapshot, check_views
from first48.collect import is_article


def pages(n):
    return [{"page_id": i, "title": f"Page {i}", "t0": "2026-11-01T10:00:00Z"} for i in range(1, n + 1)]


def states_for(new_pages, n_articles):
    return [
        {"page_id": p["page_id"], "exists": True, "namespace": 0, "is_redirect": i >= n_articles}
        for i, p in enumerate(new_pages)
    ]


def test_normal_day_passes():
    new = pages(1000)
    assert check_snapshot(new, states_for(new, 350), is_article) == []


def test_too_few_pages_fails():
    new = pages(50)
    assert check_snapshot(new, states_for(new, 20), is_article)


def test_snapshot_missing_pages_fails():
    new = pages(1000)
    problems = check_snapshot(new, states_for(new, 350)[:900], is_article)
    assert any("snapshot covers" in p for p in problems)


def test_no_articles_fails():
    new = pages(1000)
    assert check_snapshot(new, states_for(new, 0), is_article)


def test_views_pass_and_fail():
    cohort = dt.date(2026, 11, 1)
    good = [{"page_id": 1, "views": {"2026-11-01": 5, "2026-11-02": 0}}]
    assert check_views(good, 1, cohort, 2) == []
    assert check_views(good, 2, cohort, 2)

    outside = [{"page_id": 1, "views": {"2026-11-03": 5}}]
    assert check_views(outside, 1, cohort, 2)

    negative = [{"page_id": 1, "views": {"2026-11-01": -1}}]
    assert check_views(negative, 1, cohort, 2)
