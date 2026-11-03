"""Final holdout: the last 6 weeks of complete cohorts, scored once.

Models train on cohorts whose labels are known at the holdout start (created
on or before HOLDOUT_START - 30 days) and are scored on every article
created from HOLDOUT_START to the end of the backfill. The script refuses to
run a second time unless the earlier output is deleted by hand.

    python -m first48.holdout
"""
import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from first48.backtest import BASELINES, HOLDOUT_START, SEEDS, load_articles, predict_fold, split
from first48.compare import MODELS as CONTENT_MODELS
from first48.compare import seed_averaged_errors, with_embeddings
from first48.flag import flag_metrics, flag_table
from first48.intervals import coverage_by_d1, predict_intervals
from first48.metrics import interval_metrics, log_error, paired_bootstrap, point_metrics

HOLDOUT_DAYS = 42


def lightgbm_errors(preds):
    seed_cols = [f"lightgbm_seed{s}" for s in SEEDS]
    return np.mean([log_error(preds[c], preds["views_30d"]) for c in seed_cols], axis=0)


def point_results(preds):
    rows = []
    for name in BASELINES:
        rows.append({"model": name, **point_metrics(preds[name], preds["views_30d"])})
    per_seed = [point_metrics(preds[f"lightgbm_seed{s}"], preds["views_30d"]) for s in SEEDS]
    rows.append({"model": "lightgbm", **pd.DataFrame(per_seed).mean().to_dict()})
    return pd.DataFrame(rows)


def comparisons(preds):
    lgb_err = lightgbm_errors(preds)
    rows = []
    for name in BASELINES:
        est, lo, hi = paired_bootstrap(log_error(preds[name], preds["views_30d"]), lgb_err)
        rows.append({"baseline": name, "baseline_minus_lightgbm": est, "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(rows)


def by_type(preds, articles):
    df = preds.merge(articles[["page_id", "article_type"]], on="page_id")
    df["lightgbm_err"] = lightgbm_errors(df)
    rows = []
    for article_type, group in df.groupby("article_type"):
        row = {"article_type": article_type, "n": len(group),
               "lightgbm": float(np.median(group["lightgbm_err"]))}
        for name in BASELINES:
            row[name] = float(np.median(log_error(group[name], group["views_30d"])))
        rows.append(row)
    return pd.DataFrame(rows)


def content_results(articles, embeddings):
    """Amendment 1 comparison on the holdout articles that have text."""
    df = with_embeddings(articles, embeddings)
    train, test = split(df, HOLDOUT_START, test_days=HOLDOUT_DAYS)
    preds = test[["page_id", "views_30d"]].copy()
    for name, make in CONTENT_MODELS.items():
        for seed in SEEDS:
            preds[f"{name}_seed{seed}"] = make(seed).fit(train).predict(test)
    rows = []
    for name in CONTENT_MODELS:
        per_seed = [point_metrics(preds[f"{name}_seed{s}"], preds["views_30d"]) for s in SEEDS]
        rows.append({"model": name, "n": len(preds), **pd.DataFrame(per_seed).mean().to_dict()})
    est, lo, hi = paired_bootstrap(seed_averaged_errors(preds, "content_only"),
                                   seed_averaged_errors(preds, "combined"))
    added = pd.DataFrame([{"articles": len(preds), "content_minus_combined": est, "ci_low": lo, "ci_high": hi}])
    return pd.DataFrame(rows), added


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--out", type=Path, default=Path("results/holdout"))
    parser.add_argument("--embeddings", type=Path, default=Path("data/embeddings.parquet"))
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists: the holdout has already been scored")

    articles = load_articles(args.db)
    train, test = split(articles, HOLDOUT_START, test_days=HOLDOUT_DAYS)
    expected_end = HOLDOUT_START + dt.timedelta(days=HOLDOUT_DAYS - 1)
    if test["cohort_date"].max() != expected_end:
        raise SystemExit(f"holdout should end on {expected_end}, data ends on {test['cohort_date'].max()}")

    preds = predict_fold(train, test)
    preds.insert(0, "origin", HOLDOUT_START)
    preds.insert(1, "page_id", test["page_id"].to_numpy())
    preds.insert(2, "views_30d", test["views_30d"].to_numpy())

    intervals = pd.concat([predict_intervals(train, test, seed).assign(seed=seed) for seed in SEEDS])
    intervals["views_30d"] = np.tile(test["views_30d"].to_numpy(), len(SEEDS))
    intervals["views_d1"] = np.tile(test["views_d1"].to_numpy(), len(SEEDS))
    coverage = pd.DataFrame([
        {"seed": seed, **interval_metrics(g["cqr_lower"], g["cqr_upper"], g["views_30d"]),
         "quantile_coverage": interval_metrics(g["q10"], g["q90"], g["views_30d"])["coverage"]}
        for seed, g in intervals.groupby("seed")
    ])

    args.out.mkdir(parents=True)
    point_results(preds).to_csv(args.out / "point.csv", index=False)
    comparisons(preds).to_csv(args.out / "point_vs_baselines.csv", index=False)
    by_type(preds, articles).to_csv(args.out / "point_by_type.csv", index=False)
    coverage.to_csv(args.out / "intervals.csv", index=False)
    coverage_by_d1(intervals).to_csv(args.out / "intervals_by_d1.csv")
    flag_metrics(flag_table(preds, articles)).to_csv(args.out / "flag.csv", index=False)
    (args.out / "split.json").write_text(json.dumps({
        "train_cohorts": f"{train['cohort_date'].min()} to {train['cohort_date'].max()}",
        "train_articles": len(train),
        "holdout_cohorts": f"{test['cohort_date'].min()} to {test['cohort_date'].max()}",
        "holdout_articles": len(test),
    }, indent=2))
    if args.embeddings.exists():
        content, added = content_results(articles, args.embeddings)
        content.to_csv(args.out / "content.csv", index=False)
        added.to_csv(args.out / "content_added_value.csv", index=False)
    preds.to_parquet(args.db.with_name("holdout_predictions.parquet"))
    print(f"holdout scored: {len(test):,} articles, results in {args.out}")


if __name__ == "__main__":
    main()
