import datetime as dt

import numpy as np

from first48.horizons import GradientBoostingDays, PintoDays, later_days, run
from tests.test_backtest import articles


def with_later_days(df):
    for d in range(2, 8):
        df[f"views_d{d}"] = df["views_d1"]
    return df


def test_later_days_are_the_ones_before_the_forecast_day():
    assert later_days(2) == []
    assert later_days(4) == ["views_d2", "views_d3"]


def test_pinto_days_uses_one_slope_per_known_day():
    df = with_later_days(articles(dt.date(2026, 1, 1), 5))
    assert PintoDays(4).design(df).shape == (len(df), 5)


def test_day_8_model_sees_six_more_columns_than_day_2():
    df = with_later_days(articles(dt.date(2026, 1, 1), 5))
    extra = GradientBoostingDays(8).matrix(df).shape[1] - GradientBoostingDays(2).matrix(df).shape[1]
    assert extra == 6


def test_run_scores_every_horizon_per_origin():
    df = with_later_days(articles(dt.date(2026, 1, 1), 80)).assign(edits_d0=1, edits_48h=2, editors_48h=1,
                                                                  size_d0=100, size_d1=120)
    folds = run(df, [dt.date(2026, 3, 1)])
    assert folds["forecast_day"].tolist() == [2, 4, 8]
    assert np.isfinite(folds[["pinto_style", "lightgbm"]].to_numpy()).all()


def test_share_seen_counts_known_days_only():
    import pandas as pd

    from first48.horizons import share_seen

    df = pd.DataFrame({"views_d0": [10], "views_d1": [10], "views_d2": [5], "views_d3": [5],
                       "views_d4": [0], "views_d5": [0], "views_d6": [0], "views_d7": [0], "views_30d": [100]})
    assert share_seen(df)["median_share_seen"].tolist() == [0.2, 0.3, 0.3]
