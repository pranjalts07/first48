import datetime as dt

from first48.yoy import months, run
from tests.test_backtest import articles


def test_months_stop_before_end():
    assert list(months(dt.date(2025, 11, 1), dt.date(2026, 2, 15))) == [
        dt.date(2025, 11, 1), dt.date(2025, 12, 1), dt.date(2026, 1, 1), dt.date(2026, 2, 1)]


def test_one_row_per_2026_month_with_data():
    df = articles(dt.date(2025, 10, 1), 150)
    out = run(df)
    assert list(out["month"]) == ["2026-01", "2026-02"]
    assert (out["articles"] > 0).all()
