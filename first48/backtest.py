"""Rolling-origin backtests of the point forecasts.

At each origin T the models train on articles created on or before T - 30
days, the last cohorts whose 30-day views are known at T, and are scored on
articles created in the 7 days from T. Articles created on or after
HOLDOUT_START are never used here; they are the final holdout.

    python -m first48.backtest
"""
import argparse
import datetime as dt
from pathlib import Path

import duckdb
import mlflow
import pandas as pd

from first48.metrics import point_metrics
from first48.models import FlatRate, GradientBoosting, LogLinear, PintoStyle, SzaboHuberman, SzaboHubermanLog

LABEL_LAG = 30
TEST_DAYS = 7
ORIGINS = [dt.date(2025 + (m - 1) // 12, (m - 1) % 12 + 1, 1) for m in range(3, 21)]
HOLDOUT_START = dt.date(2026, 8, 20)
SEEDS = range(5)

BASELINES = {
    "flat_rate": FlatRate,
    "szabo_huberman": SzaboHuberman,
    "szabo_huberman_log": SzaboHubermanLog,
    "pinto_style": PintoStyle,
    "log_linear": LogLinear,
}


def load_articles(db):
    con = duckdb.connect(str(db), read_only=True)
    df = con.execute("select * from fct_articles where dataset = 'backfill'").df()
    df["cohort_date"] = pd.to_datetime(df["cohort_date"]).dt.date
    return df


def split(articles, origin, test_days=TEST_DAYS):
    train = articles[articles["cohort_date"] <= origin - dt.timedelta(days=LABEL_LAG)]
    test_end = origin + dt.timedelta(days=test_days)
    test = articles[(articles["cohort_date"] >= origin) & (articles["cohort_date"] < test_end)]
    return train, test


def predict_fold(train, test):
    """Predictions for one fold: one column per model, seeded models once per seed."""
    preds = {name: model().fit(train).predict(test) for name, model in BASELINES.items()}
    for seed in SEEDS:
        preds[f"lightgbm_seed{seed}"] = GradientBoosting(seed=seed).fit(train).predict(test)
        preds[f"lightgbm_no_edits_seed{seed}"] = GradientBoosting(seed=seed, edits=False).fit(train).predict(test)
    return pd.DataFrame(preds, index=test.index)


def run(articles, origins):
    folds = []
    for origin in origins:
        train, test = split(articles, origin)
        if test["cohort_date"].max() >= HOLDOUT_START:
            raise ValueError(f"origin {origin} reaches into the final holdout")
        if train.empty or test.empty:
            print(f"{origin}: no data, skipped")
            continue
        preds = predict_fold(train, test)
        preds.insert(0, "origin", origin)
        preds.insert(1, "page_id", test["page_id"])
        preds.insert(2, "views_30d", test["views_30d"])
        folds.append(preds)
        print(f"{origin}: trained on {len(train):,}, tested on {len(test):,}")
    return pd.concat(folds, ignore_index=True)


def fold_metrics(preds):
    model_cols = [c for c in preds.columns if c not in ("origin", "page_id", "views_30d")]
    rows = []
    for origin, fold in preds.groupby("origin"):
        for col in model_cols:
            model, _, seed = col.partition("_seed")
            row = {"origin": origin, "model": model, "seed": int(seed) if seed else None, "n": len(fold)}
            row.update(point_metrics(fold[col], fold["views_30d"]))
            rows.append(row)
    return pd.DataFrame(rows)


def summarize(metrics):
    # Seeded models are averaged over seeds within a fold first.
    by_fold = metrics.groupby(["origin", "model"], as_index=False).mean(numeric_only=True)
    summary = by_fold.groupby("model").agg(
        folds=("origin", "nunique"),
        median_abs_log_error=("median_abs_log_error", "mean"),
        mean_abs_log_error=("mean_abs_log_error", "mean"),
        smape=("smape", "mean"),
    )
    pivot = by_fold.pivot(index="origin", columns="model", values="median_abs_log_error")
    for baseline in BASELINES:
        if "lightgbm" in pivot:
            summary.loc["lightgbm", f"folds_beating_{baseline}"] = (pivot["lightgbm"] < pivot[baseline]).sum()
    return summary.sort_values("median_abs_log_error")


def log_to_mlflow(metrics, origins):
    mlflow.set_experiment("point-backtest")
    by_fold = metrics.groupby(["origin", "model"], as_index=False).mean(numeric_only=True)
    for model, rows in by_fold.groupby("model"):
        with mlflow.start_run(run_name=model):
            mlflow.log_params({
                "model": model,
                "origins": ",".join(str(o) for o in origins),
                "label_lag_days": LABEL_LAG,
                "test_days": TEST_DAYS,
                "seeds": len(SEEDS) if model == "lightgbm" else 1,
            })
            for step, row in enumerate(rows.sort_values("origin").itertuples()):
                mlflow.log_metric("median_abs_log_error", row.median_abs_log_error, step=step)
                mlflow.log_metric("mean_abs_log_error", row.mean_abs_log_error, step=step)
            mlflow.log_metric("avg_median_abs_log_error", rows["median_abs_log_error"].mean())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--origins", nargs="*", type=dt.date.fromisoformat, default=ORIGINS)
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()

    preds = run(load_articles(args.db), args.origins)
    metrics = fold_metrics(preds)
    args.out.mkdir(exist_ok=True)
    metrics.to_csv(args.out / "backtest_point_folds.csv", index=False)
    preds.to_parquet(Path("data") / "backtest_point_predictions.parquet")
    if not args.no_mlflow:
        log_to_mlflow(metrics, args.origins)
    print(summarize(metrics).round(3).to_string())


if __name__ == "__main__":
    main()
