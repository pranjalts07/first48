import datetime as dt

from first48.backfill import cohort_days, todo


def test_cohort_days_includes_both_ends():
    days = list(cohort_days(dt.date(2026, 1, 30), dt.date(2026, 2, 2)))
    assert days == [dt.date(2026, 1, 30), dt.date(2026, 1, 31), dt.date(2026, 2, 1), dt.date(2026, 2, 2)]


def test_todo_skips_finished_cohorts(tmp_path):
    (tmp_path / "views_full_2026-01-02.jsonl").write_text("")
    days = todo(dt.date(2026, 1, 1), dt.date(2026, 1, 3), tmp_path)
    assert days == [dt.date(2026, 1, 1), dt.date(2026, 1, 3)]
