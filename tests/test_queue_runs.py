import datetime as dt

from first48.queue_runs import DAYS_2026, days, next_runs

ALL_2026 = set(days(*DAYS_2026))


def test_2026_gaps_come_before_2025_months():
    have = ALL_2026 - {dt.date(2026, 7, 10), dt.date(2026, 7, 11)}
    runs = dict(next_runs(have, have, set(), set(), set()))
    assert runs["backfill.yml"] == {"start": dt.date(2026, 7, 10), "end": dt.date(2026, 7, 11)}


def test_2025_month_is_bundled_once_2026_is_complete():
    runs = dict(next_runs(ALL_2026, ALL_2026, {"2025-01"}, ALL_2026, set()))
    assert runs["backfill.yml"] == {"start": dt.date(2025, 2, 1), "end": dt.date(2025, 2, 28), "bundle": "true"}
    assert "content.yml" not in runs


def test_content_runs_are_capped_at_30_days():
    runs = dict(next_runs(ALL_2026, ALL_2026, set(), set(), set()))
    assert runs["content.yml"] == {"start": dt.date(2026, 1, 1), "end": dt.date(2026, 1, 30)}


def test_edits_wait_for_a_complete_month():
    have = set(days(dt.date(2026, 1, 1), dt.date(2026, 2, 27)))
    runs = dict(next_runs(have, have, set(), set(), {"2026-01"}))
    assert "edits.yml" not in runs
    runs = dict(next_runs(have, have, {"2025-03"}, set(), {"2026-01"}))
    assert runs["edits.yml"] == {"month": "2025-03"}


def test_nothing_left_means_no_runs():
    months = {f"2025-{m:02d}" for m in range(1, 13)} | {f"2026-{m:02d}" for m in range(1, 10)}
    assert next_runs(ALL_2026, ALL_2026, months, ALL_2026, months) == []
