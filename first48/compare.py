"""What do the first two days of views add beyond content known at creation?

Three LightGBM models on the same articles, folds and seeds (PLAN.md,
Amendment 1):
- content only: text at the end of day 0 plus article type, no views
- early signal: the plan-v1 model
- combined: early-signal features plus text at the end of day 1

Text was fetched for 2026 cohorts only (Amendment 3), so the comparison uses
2026 cohorts and the plan-v1 origins.

    python -m first48.embed
    python -m first48.compare
"""
import argparse
import datetime as dt
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd

from first48.backtest import HOLDOUT_START, SEEDS, load_articles, split
from first48.metrics import log_error, paired_bootstrap, point_metrics
from first48.models import ContentGradientBoosting, GradientBoosting

CONTENT_START = dt.date(2026, 1, 1)
ORIGINS = [dt.date(2026, month, 1) for month in range(3, 9)]

MODELS = {
    "content_only": lambda seed: ContentGradientBoosting("d0", with_views=False, seed=seed),
    "early_signal": lambda seed: GradientBoosting(seed=seed),
    "combined": lambda seed: ContentGradientBoosting("d1", with_views=True, seed=seed),
}


def with_embeddings(articles, path):
    emb = pd.read_parquet(path)
    df = articles[articles["cohort_date"] >= CONTENT_START].merge(emb, on="page_id", how="inner")
    dim = len(next(v for v in emb["emb_d0"] if v is not None))
    for col in ("emb_d0", "emb_d1"):
        df[col] = [v if v is not None else np.full(dim, np.nan, dtype=np.float32) for v in df[col]]
    return df


def run(articles, origins):
    folds = []
    for origin in origins:
        train, test = split(articles, origin)
        if test["cohort_date"].max() >= HOLDOUT_START:
            raise ValueError(f"origin {origin} reaches into the final holdout")
        if train.empty or test.empty:
            continue
        out = test[["page_id", "views_30d"]].copy()
        out.insert(0, "origin", origin)
        for name, make in MODELS.items():
            for seed in SEEDS:
                out[f"{name}_seed{seed}"] = make(seed).fit(train).predict(test)
        folds.append(out)
        print(f"{origin}: trained on {len(train):,}, tested on {len(test):,}")
    return pd.concat(folds, ignore_index=True)


def summarize(preds):
    rows = []
    for origin, fold in preds.groupby("origin"):
        for name in MODELS:
            per_seed = [point_metrics(fold[f"{name}_seed{s}"], fold["views_30d"]) for s in SEEDS]
            row = pd.DataFrame(per_seed).mean().to_dict()
            rows.append({"origin": origin, "model": name, "n": len(fold), **row})
    return pd.DataFrame(rows)


def seed_averaged_errors(preds, name):
    errors = [log_error(preds[f"{name}_seed{s}"], preds["views_30d"]) for s in SEEDS]
    return np.mean(errors, axis=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--embeddings", type=Path, default=Path("data/embeddings.parquet"))
    parser.add_argument("--origins", nargs="*", type=dt.date.fromisoformat, default=ORIGINS)
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()

    articles = with_embeddings(load_articles(args.db), args.embeddings)
    preds = run(articles, args.origins)
    metrics = summarize(preds)
    args.out.mkdir(exist_ok=True)
    metrics.to_csv(args.out / "compare_folds.csv", index=False)

    content = seed_averaged_errors(preds, "content_only")
    combined = seed_averaged_errors(preds, "combined")
    est, lo, hi = paired_bootstrap(content, combined)
    added = pd.DataFrame([{"articles": len(preds), "content_minus_combined": est, "ci_low": lo, "ci_high": hi}])
    added.to_csv(args.out / "compare_added_value.csv", index=False)

    if not args.no_mlflow:
        mlflow.set_experiment("content-comparison")
        for name, rows in metrics.groupby("model"):
            with mlflow.start_run(run_name=name):
                mlflow.log_params({"model": name, "seeds": len(SEEDS),
                                   "origins": ",".join(str(o) for o in args.origins)})
                mlflow.log_metric("avg_median_abs_log_error", rows["median_abs_log_error"].mean())

    print(metrics.groupby("model")[["median_abs_log_error", "mean_abs_log_error"]].mean().round(3).to_string())
    print(f"Median abs log error, content only minus combined: {est:.3f} (95% CI {lo:.3f} to {hi:.3f})")


if __name__ == "__main__":
    main()
