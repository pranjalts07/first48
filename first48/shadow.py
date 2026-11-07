"""Shadow mode: forecasts for live articles, written before outcomes exist.

    python -m first48.shadow train      # fit on backfilled cohorts, save to models/
    python -m first48.shadow predict    # forecast live cohorts that have day 0 and 1 views
    python -m first48.shadow monitor    # input and prediction drift per cohort
    python -m first48.shadow score      # compare forecasts with 30-day views once known

Nothing here acts on a forecast. Predictions are stored with the time they
were made, so scoring later shows how the model would have done live.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

from first48.backtest import SEEDS, load_articles
from first48.flag import top_share
from first48.intervals import CAL_DAYS, LEVEL, conformal_margin
from first48.metrics import interval_metrics, point_metrics
from first48.models import GradientBoosting, features

PSI_ALERT = 0.25
COVERAGE_RANGE = (0.70, 0.90)


def psi(reference_share, values, edges):
    """Population stability index of values against reference bin shares."""
    counts = np.histogram(values, bins=edges)[0]
    share = np.clip(counts / max(counts.sum(), 1), 1e-4, None)
    ref = np.clip(np.asarray(reference_share), 1e-4, None)
    return float(np.sum((share - ref) * np.log(share / ref)))


def reference(values, n_bins=10):
    edges = np.unique(np.quantile(values, np.linspace(0, 1, n_bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf
    share = np.histogram(values, bins=edges)[0] / len(values)
    return {"edges": edges.tolist(), "share": share.tolist()}


def train(articles, model_dir):
    model_dir.mkdir(parents=True, exist_ok=True)
    last = articles["cohort_date"].max()
    proper = articles[articles["cohort_date"] <= last - dt.timedelta(days=CAL_DAYS)]
    cal = articles[articles["cohort_date"] > last - dt.timedelta(days=CAL_DAYS)]

    for seed in SEEDS:
        model = GradientBoosting(seed=seed).fit(articles)
        model.model.booster_.save_model(model_dir / f"point_seed{seed}.txt")
    alpha = (1 - LEVEL) / 2
    bands = {}
    for name, q in (("lower", alpha), ("upper", 1 - alpha)):
        model = GradientBoosting(seed=0, alpha=q).fit(proper)
        model.model.booster_.save_model(model_dir / f"quantile_{name}.txt")
        bands[name] = np.log1p(model.predict(cal))
    margin = conformal_margin(bands["lower"], bands["upper"], np.log1p(cal["views_30d"].to_numpy()))

    point = predict(articles, model_dir, margin=margin)
    meta = {
        "trained_on": f"{articles['cohort_date'].min()} to {last}",
        "articles": len(articles),
        "level": LEVEL,
        "margin": float(margin),
        "reference_log_d1": reference(np.log1p(articles["views_d1"])),
        "reference_log_pred": reference(np.log1p(point["pred"])),
    }
    (model_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def predict(early, model_dir, margin=None):
    if margin is None:
        margin = json.loads((model_dir / "meta.json").read_text())["margin"]
    X = features(early, edits=True)
    point = np.mean([lgb.Booster(model_file=str(model_dir / f"point_seed{s}.txt")).predict(X) for s in SEEDS], axis=0)
    lower = lgb.Booster(model_file=str(model_dir / "quantile_lower.txt")).predict(X) - margin
    upper = lgb.Booster(model_file=str(model_dir / "quantile_upper.txt")).predict(X) + margin
    out = pd.DataFrame({
        "page_id": early["page_id"].to_numpy(),
        "cohort_date": early["cohort_date"].astype(str).to_numpy(),
        "pred": np.expm1(point).clip(min=0),
        "lower": np.expm1(np.maximum(lower, 0)),
        "upper": np.expm1(upper),
    })
    out["flag"] = top_share(out["pred"], out["cohort_date"]).to_numpy()
    return out


def monitor_rows(early, preds, meta):
    rows = []
    for cohort, group in early.groupby("cohort_date"):
        p = preds[preds["cohort_date"] == str(cohort)]
        ref_d1, ref_pred = meta["reference_log_d1"], meta["reference_log_pred"]
        rows.append({
            "cohort_date": str(cohort),
            "articles": len(group),
            "median_views_d1": float(group["views_d1"].median()),
            "median_pred": float(p["pred"].median()),
            "psi_log_d1": psi(ref_d1["share"], np.log1p(group["views_d1"]), ref_d1["edges"]),
            "psi_log_pred": psi(ref_pred["share"], np.log1p(p["pred"]), ref_pred["edges"]),
        })
    return pd.DataFrame(rows)


def alerts(monitoring, scores):
    lines = [f"{r.cohort_date}: input drift, PSI of log day-1 views {r.psi_log_d1:.2f}"
             for r in monitoring.itertuples() if r.psi_log_d1 > PSI_ALERT]
    lines += [f"{r.cohort_date}: prediction drift, PSI of log forecasts {r.psi_log_pred:.2f}"
              for r in monitoring.itertuples() if r.psi_log_pred > PSI_ALERT]
    if scores is not None:
        lo, hi = COVERAGE_RANGE
        lines += [f"{r.cohort_date}: 80% range covered {r.coverage:.0%} of articles"
                  for r in scores.itertuples() if not lo <= r.coverage <= hi]
    return lines


def load_table(db, table):
    con = duckdb.connect(str(db), read_only=True)
    df = con.execute(f"select * from {table}").df()
    df["cohort_date"] = pd.to_datetime(df["cohort_date"]).dt.date
    return df


def read_predictions(folder):
    files = sorted(Path(folder).glob("shadow_*.jsonl"))
    return pd.concat([pd.read_json(f, lines=True, dtype={"cohort_date": str}) for f in files]) if files else None


def score(preds, live):
    df = preds.merge(live[["page_id", "views_30d"]], on="page_id")
    rows = []
    for cohort, group in df.groupby("cohort_date"):
        rows.append({
            "cohort_date": cohort,
            "articles": len(group),
            **point_metrics(group["pred"], group["views_30d"]),
            **interval_metrics(group["lower"], group["upper"], group["views_30d"]),
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["train", "predict", "monitor", "score"])
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--models", type=Path, default=Path("models"))
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--report", type=Path, default=Path("."), help="folder for monitoring files")
    args = parser.parse_args()

    if args.command == "train":
        print(json.dumps({k: v for k, v in train(load_articles(args.db), args.models).items()
                          if not k.startswith("reference")}, indent=2))
        return

    early = load_table(args.db, "fct_early_views")
    if args.command == "predict":
        made_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for cohort, group in early.groupby("cohort_date"):
            path = args.raw / f"shadow_{cohort}.jsonl"
            if path.exists():
                continue
            out = predict(group, args.models)
            out["predicted_at"] = made_at
            out.to_json(path, orient="records", lines=True)
            print(path)
        return

    preds = read_predictions(args.raw)
    if preds is None:
        return
    live = load_table(args.db, "fct_articles")
    scores = score(preds, live[live["dataset"] == "live"])
    if args.command == "score":
        print(scores.round(3).to_string(index=False))
        return

    meta = json.loads((args.models / "meta.json").read_text())
    monitoring = monitor_rows(early, preds, meta)
    monitoring.to_csv(args.report / "monitoring.csv", index=False)
    if not scores.empty:
        scores.to_csv(args.report / "shadow_scores.csv", index=False)
    # Alert on the newest cohort only, so an old alert is not raised every day.
    lines = alerts(monitoring.tail(1), scores.tail(1) if not scores.empty else None)
    (args.report / "alerts.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
    print(monitoring.round(3).to_string(index=False))
    print("\n".join(lines) or "no alerts")


if __name__ == "__main__":
    main()
