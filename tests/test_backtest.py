import datetime as dt

import pandas as pd
import pytest

from first48.backtest import run, split


def articles(start, days):
    rows = []
    for i in range(days):
        day = start + dt.timedelta(days=i)
        for j in range(20):
            d0, d1 = j + 1, j + 2
            rows.append({
                "page_id": i * 100 + j, "cohort_date": day, "t0": pd.Timestamp(day) + pd.Timedelta(hours=j),
                "creation_hour": j, "weekday": day.isoweekday(), "source": "create", "article_type": "other",
                "views_d0": d0, "views_d1": d1, "views_48h": d0 + d1, "views_30d": 10 * (d0 + d1),
            })
    return pd.DataFrame(rows)


def test_training_stops_30_days_before_origin():
    df = articles(dt.date(2026, 1, 1), 60)
    train, test = split(df, dt.date(2026, 2, 15))
    assert train["cohort_date"].max() == dt.date(2026, 1, 16)
    assert test["cohort_date"].min() == dt.date(2026, 2, 15)
    assert test["cohort_date"].max() == dt.date(2026, 2, 21)


def test_no_overlap_between_train_and_test():
    df = articles(dt.date(2026, 1, 1), 60)
    train, test = split(df, dt.date(2026, 2, 15))
    assert set(train["page_id"]).isdisjoint(test["page_id"])


def test_origin_inside_holdout_is_refused():
    df = articles(dt.date(2026, 7, 1), 60)
    with pytest.raises(ValueError):
        run(df, [dt.date(2026, 8, 15)])


def test_content_model_uses_embeddings():
    import numpy as np
    from first48.models import ContentGradientBoosting

    df = articles(dt.date(2026, 1, 1), 10)
    rng = np.random.default_rng(0)
    df["emb_d0"] = list(rng.normal(size=(len(df), 4)).astype(np.float32))
    df["emb_d1"] = df["emb_d0"]
    for with_views in (False, True):
        model = ContentGradientBoosting("d0", with_views=with_views)
        pred = model.fit(df).predict(df)
        assert pred.shape == (len(df),)
        assert (pred >= 0).all()
