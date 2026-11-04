"""Year-over-year check: how much does a model trained only on 2025 lose in 2026?

For each 2026 month before the holdout, two LightGBM models are scored on
that month's articles: one trained on 2025 cohorts only, and one trained on
every cohort whose label is known at the start of the month. Flat rate,
which needs no training, is the reference.

    python -m first48.yoy
"""
import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from first48.backtest import HOLDOUT_START, LABEL_LAG, SEEDS, load_articles
from first48.metrics import log_error
from first48.models import FlatRate, GradientBoosting

TRAIN_END = dt.date(2025, 12, 31)


def months(start, end):
    month = start
    while month < end:
        yield month
        month = dt.date(month.year + month.month // 12, month.month % 12 + 1, 1)


def seed_averaged_error(train, test):
    errors = [log_error(GradientBoosting(seed=s).fit(train).predict(test), test["views_30d"]) for s in SEEDS]
    return float(np.median(np.mean(errors, axis=0)))


def run(articles):
    last_year = articles[articles["cohort_date"] <= TRAIN_END]
    rows = []
    for month in months(dt.date(2026, 1, 1), HOLDOUT_START):
        next_month = dt.date(month.year + month.month // 12, month.month % 12 + 1, 1)
        test = articles[(articles["cohort_date"] >= month)
                        & (articles["cohort_date"] < min(next_month, HOLDOUT_START))]
        recent = articles[articles["cohort_date"] <= month - dt.timedelta(days=LABEL_LAG)]
        if test.empty:
            continue
        rows.append({
            "month": month.isoformat()[:7],
            "articles": len(test),
            "trained_on_2025": seed_averaged_error(last_year, test),
            "retrained_monthly": seed_averaged_error(recent, test),
            "flat_rate": float(np.median(log_error(FlatRate().fit(recent).predict(test), test["views_30d"]))),
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()
    out = run(load_articles(args.db))
    args.out.mkdir(exist_ok=True)
    out.to_csv(args.out / "yoy.csv", index=False)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
