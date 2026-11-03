"""Correlation between early and 30-day views on the log scale.

Reported for all pre-holdout cohorts with a bootstrap 95% interval, and
separately for weekday and weekend creation days, as PLAN.md asks.

    python -m first48.correlation
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from first48.backtest import HOLDOUT_START, load_articles


def log_corr(df):
    return float(np.corrcoef(np.log1p(df["views_48h"]), np.log1p(df["views_30d"]))[0, 1])


def bootstrap_corr(df, n_boot=1000, seed=0):
    rng = np.random.default_rng(seed)
    x, y = np.log1p(df["views_48h"].to_numpy()), np.log1p(df["views_30d"].to_numpy())
    stats = []
    for _ in range(n_boot):
        i = rng.integers(0, len(x), size=len(x))
        stats.append(np.corrcoef(x[i], y[i])[0, 1])
    return float(np.quantile(stats, 0.025)), float(np.quantile(stats, 0.975))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    articles = load_articles(args.db)
    articles = articles[articles["cohort_date"] < HOLDOUT_START]
    groups = {
        "all": articles,
        "weekday": articles[articles["weekday"] <= 5],
        "weekend": articles[articles["weekday"] >= 6],
    }
    rows = []
    for name, df in groups.items():
        lo, hi = bootstrap_corr(df)
        rows.append({"group": name, "articles": len(df), "correlation": log_corr(df), "ci_low": lo, "ci_high": hi})
    daily = articles.groupby("cohort_date").apply(log_corr, include_groups=False)
    rows.append({"group": "single days, min", "articles": None, "correlation": daily.min()})
    rows.append({"group": "single days, max", "articles": None, "correlation": daily.max()})
    out = pd.DataFrame(rows)
    args.out.mkdir(exist_ok=True)
    out.to_csv(args.out / "correlation.csv", index=False)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
