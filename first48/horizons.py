"""How much does waiting help? Forecasts made at the end of day 1, 3 and 7.

Amendment 3: the same models, given views for more days, scored on the same
rolling origins and seeds. The target is still views on days 0 to 29, so a
later forecast already knows part of it. The final holdout is not used; the
day-2 forecast remains the primary result.

    python -m first48.horizons
"""
import argparse
import datetime as dt
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from first48.backtest import HOLDOUT_START, ORIGINS, SEEDS, load_articles, split
from first48.metrics import log_error
from first48.models import GradientBoosting, PintoStyle

HORIZONS = [2, 4, 8]


def load_daily(db, last_day=max(HORIZONS) - 1):
    con = duckdb.connect(str(db), read_only=True)
    daily = con.execute(
        "select page_id, day_index, views from stg_daily_views "
        "where kind = 'full' and dataset = 'backfill' and day_index between 2 and ?", [last_day]).df()
    wide = daily.pivot(index="page_id", columns="day_index", values="views")
    return wide.add_prefix("views_d").reset_index()


def later_days(days):
    return [f"views_d{d}" for d in range(2, days)]


class PintoDays(PintoStyle):
    """log Y on log views of each known day, each with its own slope."""

    def __init__(self, days):
        self.cols = ["views_d0", "views_d1", *later_days(days)]

    def design(self, df):
        return np.column_stack([np.ones(len(df)), np.log1p(df[self.cols].to_numpy(dtype=float))])


class GradientBoostingDays(GradientBoosting):
    """The day-2 LightGBM plus log views of each later known day."""

    def __init__(self, days, seed=0):
        super().__init__(seed=seed)
        self.extra = later_days(days)

    def matrix(self, df):
        X = super().matrix(df)
        for col in self.extra:
            X[f"log_{col}"] = np.log1p(df[col].astype(float))
        return X


def share_seen(articles):
    """Median share of the 30-day views already counted when each forecast is made."""
    rows = []
    for days in HORIZONS:
        seen = articles[["views_d0", "views_d1", *later_days(days)]].sum(axis=1)
        share = (seen / articles["views_30d"]).where(articles["views_30d"] > 0)
        rows.append({"forecast_day": days, "median_share_seen": float(share.median())})
    return pd.DataFrame(rows)


def run(articles, origins):
    rows = []
    for origin in origins:
        train, test = split(articles, origin)
        if test["cohort_date"].max() >= HOLDOUT_START:
            raise ValueError(f"origin {origin} reaches into the final holdout")
        if train.empty or test.empty:
            continue
        for days in HORIZONS:
            pinto = PintoDays(days).fit(train).predict(test)
            lgb_errors = [log_error(GradientBoostingDays(days, seed=s).fit(train).predict(test), test["views_30d"])
                          for s in SEEDS]
            rows.append({"origin": origin, "forecast_day": days, "n": len(test),
                         "pinto_style": float(np.median(log_error(pinto, test["views_30d"]))),
                         "lightgbm": float(np.median(np.mean(lgb_errors, axis=0)))})
        print(f"{origin}: trained on {len(train):,}, tested on {len(test):,}")
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--origins", nargs="*", type=dt.date.fromisoformat, default=ORIGINS)
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    articles = load_articles(args.db).merge(load_daily(args.db), on="page_id", how="left")
    folds = run(articles, args.origins)
    args.out.mkdir(exist_ok=True)
    share_seen(articles[articles["cohort_date"] < HOLDOUT_START]).to_csv(args.out / "horizons_share.csv", index=False)
    folds.to_csv(args.out / "horizons.csv", index=False)
    print(folds.groupby("forecast_day")[["pinto_style", "lightgbm"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
