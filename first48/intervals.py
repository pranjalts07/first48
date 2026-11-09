"""80% prediction intervals: LightGBM quantiles, then a conformal adjustment.

Conformalized quantile regression (Romano, Patterson and Candes, 2019):
fit the 0.1 and 0.9 quantile models on older training cohorts, measure how
far the most recent labeled cohorts fall outside those bands, and widen
(or narrow) both ends by that amount. Everything is on log(1 + views).

    python -m first48.intervals
"""
import argparse
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from first48.backtest import HOLDOUT_START, ORIGINS, SEEDS, load_articles, split
from first48.metrics import interval_metrics, pinball
from first48.models import GradientBoosting

LEVEL = 0.8
CAL_DAYS = 14
D1_BINS = [0, 5, 20, 100, np.inf]
D1_LABELS = ["0-4", "5-19", "20-99", "100+"]


def conformal_margin(lower, upper, actual, level=LEVEL):
    """The finite-sample conformal quantile of how far actuals fall outside the band."""
    scores = np.maximum(lower - actual, actual - upper)
    n = len(scores)
    k = min(n, int(np.ceil((n + 1) * level)))
    return np.sort(scores)[k - 1]


def predict_intervals(train, test, seed, cal_days=CAL_DAYS):
    last = train["cohort_date"].max()
    proper = train[train["cohort_date"] <= last - dt.timedelta(days=cal_days)]
    cal = train[train["cohort_date"] > last - dt.timedelta(days=cal_days)]

    alpha = (1 - LEVEL) / 2
    quantiles = {q: GradientBoosting(seed=seed, alpha=q).fit(proper) for q in (alpha, 0.5, 1 - alpha)}
    log = {q: lambda df, m=m: np.log1p(m.predict(df)) for q, m in quantiles.items()}

    margin = conformal_margin(log[alpha](cal), log[1 - alpha](cal), np.log1p(cal["views_30d"].to_numpy()))
    lower, upper = log[alpha](test), log[1 - alpha](test)
    return pd.DataFrame({
        "q10": np.expm1(lower),
        "q50": np.expm1(log[0.5](test)),
        "q90": np.expm1(upper),
        "cqr_lower": np.expm1(np.maximum(lower - margin, 0)),
        "cqr_upper": np.expm1(upper + margin),
        "margin": margin,
    }, index=test.index)


def run(articles, origins):
    folds = []
    for origin in origins:
        train, test = split(articles, origin)
        if test["cohort_date"].max() >= HOLDOUT_START:
            raise ValueError(f"origin {origin} reaches into the final holdout")
        if train.empty or test.empty:
            continue
        for seed in SEEDS:
            pred = predict_intervals(train, test, seed)
            pred["origin"] = origin
            pred["seed"] = seed
            pred["views_30d"] = test["views_30d"]
            pred["views_d1"] = test["views_d1"]
            folds.append(pred)
        print(f"{origin}: tested on {len(test):,}")
    return pd.concat(folds, ignore_index=True)


def fold_metrics(preds):
    rows = []
    for (origin, seed), fold in preds.groupby(["origin", "seed"]):
        y = fold["views_30d"]
        raw = interval_metrics(fold["q10"], fold["q90"], y)
        cqr = interval_metrics(fold["cqr_lower"], fold["cqr_upper"], y)
        rows.append({
            "origin": origin,
            "seed": seed,
            "n": len(fold),
            "quantile_coverage": raw["coverage"],
            "quantile_log_width": raw["mean_log_width"],
            "cqr_coverage": cqr["coverage"],
            "cqr_log_width": cqr["mean_log_width"],
            "margin": fold["margin"].iloc[0],
            "pinball_10": pinball(fold["q10"], y, 0.1),
            "pinball_50": pinball(fold["q50"], y, 0.5),
            "pinball_90": pinball(fold["q90"], y, 0.9),
        })
    return pd.DataFrame(rows)


def coverage_by_d1(preds):
    bins = pd.cut(preds["views_d1"], D1_BINS, right=False, labels=D1_LABELS)
    inside = (preds["views_30d"] >= preds["cqr_lower"]) & (preds["views_30d"] <= preds["cqr_upper"])
    return inside.groupby(bins, observed=False).agg(["mean", "size"]).rename(
        columns={"mean": "cqr_coverage", "size": "n_predictions"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--origins", nargs="*", type=dt.date.fromisoformat, default=ORIGINS)
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()

    preds = run(load_articles(args.db), args.origins)
    metrics = fold_metrics(preds)
    by_bin = coverage_by_d1(preds)
    args.out.mkdir(exist_ok=True)
    metrics.to_csv(args.out / "backtest_interval_folds.csv", index=False)
    by_bin.to_csv(args.out / "backtest_interval_coverage_by_d1.csv")

    if not args.no_mlflow:
        import mlflow

        mlflow.set_experiment("interval-backtest")
        with mlflow.start_run(run_name="lightgbm_cqr"):
            mlflow.log_params({"level": LEVEL, "cal_days": CAL_DAYS, "seeds": len(SEEDS),
                               "origins": ",".join(str(o) for o in args.origins)})
            mlflow.log_metrics(metrics.drop(columns=["origin", "seed", "n"]).mean().to_dict())

    by_fold = metrics.groupby("origin").mean(numeric_only=True).drop(columns="seed")
    print(by_fold.round(3).to_string())
    print(by_bin.round(3).to_string())


if __name__ == "__main__":
    main()
