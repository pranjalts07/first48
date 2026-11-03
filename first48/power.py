"""Sample size for the proposed experiment on acting on the flag.

Flagged articles would be randomized, half promoted and half not. The
outcome is log(1 + 30-day views). Its spread among flagged articles comes
from the backtest folds, both raw and after adjusting for the forecast
(a regression adjustment, as in CUPED), which is known before assignment.

    python -m first48.backtest   # writes the predictions this reads
    python -m first48.power
"""
import argparse
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from first48.backtest import load_articles
from first48.flag import flag_table

ALPHA = 0.05
POWER = 0.8
WEEKS = [2, 4, 8]


def mde(sd, n_per_arm, alpha=ALPHA, power=POWER):
    """Smallest true difference in means detectable with a two-sided test."""
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return z * sd * np.sqrt(2 / n_per_arm)


def flagged_spread(table):
    flagged = table[table["model_flag"]]
    y = np.log1p(flagged["views_30d"])
    x = np.log1p(flagged["model_score"])
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (intercept + slope * x)
    per_day = flagged.groupby("cohort_date").size().mean()
    return float(y.std(ddof=1)), float(resid.std(ddof=2)), float(per_day)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/first48.duckdb"))
    parser.add_argument("--preds", type=Path, default=Path("data/backtest_point_predictions.parquet"))
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    table = flag_table(pd.read_parquet(args.preds), load_articles(args.db))
    sd, sd_adjusted, per_day = flagged_spread(table)
    rows = []
    for weeks in WEEKS:
        n = int(per_day * 7 * weeks / 2)
        rows.append({
            "weeks": weeks,
            "flagged_per_arm": n,
            "mde_log": mde(sd, n),
            "mde_log_adjusted": mde(sd_adjusted, n),
        })
    out = pd.DataFrame(rows)
    out["mde_pct_adjusted"] = 100 * np.expm1(out["mde_log_adjusted"])
    args.out.mkdir(exist_ok=True)
    out.to_csv(args.out / "experiment_power.csv", index=False)
    print(f"flagged per day {per_day:.1f}, sd {sd:.3f}, sd after forecast adjustment {sd_adjusted:.3f}")
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
