"""Day-2 flag for likely top performers.

An article is a top performer if its 30-day views are in the top 5% of
articles created the same week. At the end of each article's day 1, the
top 5% of that creation day's articles by score are flagged. The current
practice baseline scores by day-1 views; the model scores by the LightGBM
forecast, averaged over seeds.

    python -m first48.backtest   # writes the predictions this reads
    python -m first48.flag
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from first48.backtest import load_articles
from first48.metrics import average_precision, precision_at_recall

TOP_SHARE = 0.05


def top_share(values, groups, share=TOP_SHARE):
    """True for the top share of values within each group, at least one per group."""
    rank = values.groupby(groups).rank(method="first", ascending=False)
    size = values.groupby(groups).transform("size")
    return rank <= np.maximum(1, np.floor(share * size))


def flag_table(preds, articles):
    df = preds[["origin", "page_id", "views_30d"]].merge(
        articles[["page_id", "cohort_date", "views_d1"]], on="page_id")
    seed_cols = [c for c in preds.columns if c.startswith("lightgbm_seed")]
    df["model_score"] = preds[seed_cols].mean(axis=1).to_numpy()
    df["baseline_score"] = df["views_d1"]
    week = pd.to_datetime(df["cohort_date"]).dt.to_period("W")
    df["top"] = top_share(df["views_30d"], [df["origin"], week])
    df["model_flag"] = top_share(df["model_score"], df["cohort_date"])
    df["baseline_flag"] = top_share(df["baseline_score"], df["cohort_date"])
    return df


def flag_metrics(df):
    rows = []
    for origin, fold in df.groupby("origin"):
        row = {"origin": origin, "n": len(fold), "top": int(fold["top"].sum())}
        for name in ("baseline", "model"):
            flagged = fold[f"{name}_flag"]
            hits = (flagged & fold["top"]).sum()
            row[f"{name}_precision"] = hits / flagged.sum()
            row[f"{name}_recall"] = hits / fold["top"].sum()
            row[f"{name}_pr_auc"] = average_precision(fold["top"], fold[f"{name}_score"])
        row["model_precision_at_baseline_recall"] = precision_at_recall(
            fold["top"], fold["model_score"], row["baseline_recall"])
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--preds", type=Path, default=Path("data/backtest_point_predictions.parquet"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    metrics = flag_metrics(flag_table(pd.read_parquet(args.preds), load_articles(args.db)))
    args.out.mkdir(exist_ok=True)
    metrics.to_csv(args.out / "backtest_flag_folds.csv", index=False)
    print(metrics.round(3).to_string(index=False))
    print(metrics.drop(columns=["origin"]).mean().round(3).to_string())


if __name__ == "__main__":
    main()
