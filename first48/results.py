"""Write RESULTS.md from the files in results/.

Every number in RESULTS.md comes from a file written by one of the scripts
below, and each section names the command that rewrites it.

    python -m first48.results
"""
import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

from first48.backtest import BASELINES

R = Path("results")


def pct(x):
    return f"{100 * x:.1f}%"


def num(x, digits=3):
    return f"{x:.{digits}f}"


def data_section(db):
    con = duckdb.connect(str(db), read_only=True)
    articles, first, last = con.execute(
        "select count(*), min(cohort_date), max(cohort_date) from fct_articles where dataset = 'backfill'").fetchone()
    rows = con.execute("select count(*) from stg_daily_views").fetchone()[0]
    pages = con.execute("select count(*) from stg_new_pages").fetchone()[0]
    live_days = con.execute("select count(distinct cohort_date) from stg_new_pages where dataset = 'live'").fetchone()[0]
    return [
        "## Data",
        "`python -m first48.warehouse`",
        "",
        f"- New pages logged: {pages:,}",
        f"- Articles with complete 30-day views (backfill, cohorts {first} to {last}): {articles:,}",
        f"- Daily view rows: {rows:,}",
        f"- Live cohorts collected so far: {live_days}",
    ]


def correlation_section():
    df = pd.read_csv(R / "correlation.csv").set_index("group")
    lines = [
        "## Early vs 30-day views",
        "`python -m first48.correlation`",
        "",
        "Correlation of log(1 + views) on days 0 and 1 with log(1 + views) on days 0 to 29, pre-holdout cohorts.",
        "",
        "| Creation days | Articles | Correlation | 95% CI |",
        "|---|---|---|---|",
    ]
    for group in ["all", "weekday", "weekend"]:
        r = df.loc[group]
        lines.append(f"| {group} | {int(r.articles):,} | {num(r.correlation)} | {num(r.ci_low)} to {num(r.ci_high)} |")
    lines += ["", f"Single creation days range from {num(df.loc['single days, min', 'correlation'])} "
                  f"to {num(df.loc['single days, max', 'correlation'])}."]
    return lines


def relative_gain(model_err, baseline_err):
    return 1 - model_err / baseline_err


def backtest_section():
    folds = pd.read_csv(R / "backtest_point_folds.csv")
    by_fold = folds.groupby(["origin", "model"], as_index=False)["median_abs_log_error"].mean()
    pivot = by_fold.pivot(index="origin", columns="model", values="median_abs_log_error")
    lines = [
        "## Rolling backtests",
        "`python -m first48.backtest`",
        "",
        f"{len(pivot)} monthly origins, test week after each, 5 seeds for LightGBM. "
        "szabo_huberman_log drops the variance correction, pinto_style uses day-0 and day-1 views separately "
        "(Amendment 4), and lightgbm_no_edits leaves out the edit activity features.",
        "",
        "| Model | Median abs log error (mean over folds) | LightGBM better by | Folds LightGBM wins |",
        "|---|---|---|---|",
    ]
    for model in [*BASELINES, "lightgbm_no_edits", "lightgbm"]:
        err = pivot[model].mean()
        if model == "lightgbm":
            lines.append(f"| {model} | {num(err)} | | |")
        else:
            gain = relative_gain(pivot["lightgbm"], pivot[model]).mean()
            wins = int((pivot["lightgbm"] < pivot[model]).sum())
            lines.append(f"| {model} | {num(err)} | {pct(gain)} | {wins} of {len(pivot)} |")
    return lines


def interval_section():
    folds = pd.read_csv(R / "backtest_interval_folds.csv")
    by_fold = folds.groupby("origin").mean(numeric_only=True)
    bins = pd.read_csv(R / "backtest_interval_coverage_by_d1.csv")
    lines = [
        "## 80% prediction ranges in backtests",
        "`python -m first48.intervals`",
        "",
        f"- Conformal ranges: mean coverage {pct(by_fold['cqr_coverage'].mean())}, "
        f"lowest fold {pct(by_fold['cqr_coverage'].min())}, highest {pct(by_fold['cqr_coverage'].max())}",
        f"- Raw quantile ranges before adjustment: {pct(by_fold['quantile_coverage'].mean())}",
        "",
        "| Day-1 views | Coverage | Predictions |",
        "|---|---|---|",
    ]
    lines += [f"| {r.views_d1} | {pct(r.cqr_coverage)} | {r.n_predictions:,} |" for r in bins.itertuples()]
    return lines


def flag_section(path, title, command):
    df = pd.read_csv(path).mean(numeric_only=True)
    return [
        f"## {title}",
        command,
        "",
        "| Rule | Precision | Recall | PR-AUC |",
        "|---|---|---|---|",
        f"| Top 5% by day-1 views (current practice) | {pct(df.baseline_precision)} | {pct(df.baseline_recall)} | {num(df.baseline_pr_auc)} |",
        f"| Top 5% by forecast | {pct(df.model_precision)} | {pct(df.model_recall)} | {num(df.model_pr_auc)} |",
        "",
        f"Forecast precision at the current-practice recall: {pct(df.model_precision_at_baseline_recall)}.",
    ]


def content_section(path, folds_path, title, command):
    added = pd.read_csv(path).iloc[0]
    df = pd.read_csv(folds_path)
    errs = df.groupby("model")["median_abs_log_error"].mean()
    return [
        f"## {title}",
        command,
        "",
        "| Model | Median abs log error |",
        "|---|---|",
        *[f"| {m} | {num(errs[m])} |" for m in ["content_only", "early_signal", "combined"]],
        "",
        f"Added value of the first two days of views (content only minus combined): "
        f"{num(added.content_minus_combined)}, 95% CI {num(added.ci_low)} to {num(added.ci_high)}, "
        f"{int(added.articles):,} articles.",
    ]


def holdout_section():
    h = R / "holdout"
    split = json.loads((h / "split.json").read_text())
    point = pd.read_csv(h / "point.csv").set_index("model")
    vs = pd.read_csv(h / "point_vs_baselines.csv").set_index("baseline")
    iv = pd.read_csv(h / "intervals.csv").mean(numeric_only=True)
    bins = pd.read_csv(h / "intervals_by_d1.csv")
    lines = [
        "## Final holdout (scored once)",
        "`python -m first48.holdout`",
        "",
        f"Trained on cohorts {split['train_cohorts']} ({split['train_articles']:,} articles), "
        f"scored on {split['holdout_cohorts']} ({split['holdout_articles']:,} articles).",
        "",
        "| Model | Median abs log error | LightGBM better by | Difference, 95% CI |",
        "|---|---|---|---|",
    ]
    lgb = point.loc["lightgbm", "median_abs_log_error"]
    for model in BASELINES:
        err = point.loc[model, "median_abs_log_error"]
        c = vs.loc[model]
        lines.append(f"| {model} | {num(err)} | {pct(relative_gain(lgb, err))} | "
                     f"{num(c.baseline_minus_lightgbm)} ({num(c.ci_low)} to {num(c.ci_high)}) |")
    lines.append(f"| lightgbm | {num(lgb)} | | |")
    lines += [
        "",
        f"80% ranges: coverage {pct(iv.coverage)} (raw quantiles {pct(iv.quantile_coverage)}), "
        f"mean width {num(iv.mean_log_width)} on the log scale.",
        "",
        "| Day-1 views | Coverage |",
        "|---|---|",
        *[f"| {r.views_d1} | {pct(r.cqr_coverage)} |" for r in bins.itertuples()],
    ]
    by_type = pd.read_csv(h / "point_by_type.csv")
    lines += ["", "| Article type | Articles | LightGBM | Flat rate | Szabo-Huberman |", "|---|---|---|---|---|"]
    lines += [f"| {r.article_type} | {r.n:,} | {num(r.lightgbm)} | {num(r.flat_rate)} | {num(r.szabo_huberman)} |"
              for r in by_type.itertuples()]
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--out", type=Path, default=Path("RESULTS.md"))
    args = parser.parse_args()

    sections = [
        ["# Results", "",
         "Generated by `python -m first48.results` from the files in results/. "
         "Each section names the command that recomputes its numbers. "
         "Errors are |log(1 + forecast) - log(1 + actual)|; a median of 0.4 means the typical forecast "
         "is off by a factor of about 1.5."],
        data_section(args.db),
    ]
    optional = [
        (R / "correlation.csv", correlation_section),
        (R / "backtest_point_folds.csv", backtest_section),
        (R / "backtest_interval_folds.csv", interval_section),
        (R / "backtest_flag_folds.csv", lambda: flag_section(
            R / "backtest_flag_folds.csv", "Day-2 flag in backtests", "`python -m first48.flag`")),
        (R / "compare_added_value.csv", lambda: content_section(
            R / "compare_added_value.csv", R / "compare_folds.csv",
            "Content only vs early views in backtests", "`python -m first48.compare`")),
        (R / "holdout" / "split.json", holdout_section),
        (R / "holdout" / "flag.csv", lambda: flag_section(
            R / "holdout" / "flag.csv", "Day-2 flag on the final holdout", "`python -m first48.holdout`")),
        (R / "timing_model.txt", lambda: [
            "## Creation timing (association only)", "`Rscript analysis/timing.R`", "",
            "Full output: results/timing_model.txt."]),
    ]
    for path, section in optional:
        if path.exists():
            sections.append(section())
    args.out.write_text("\n\n".join("\n".join(s) for s in sections) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
