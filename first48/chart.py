"""The README chart: backtest error at each origin, one line per model.

    python -m first48.backtest   # writes results/backtest_point_folds.csv
    python -m first48.chart
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

MODELS = {
    "flat_rate": ("Flat rate", "#eb6834", "s"),
    "szabo_huberman_log": ("Szabo-Huberman", "#1baf7a", "^"),
    "log_linear": ("Log-linear", "#eda100", "D"),
    "lightgbm": ("LightGBM", "#2a78d6", "o"),
}
INK = "#2b2b29"
MUTED = "#6b6a63"


def error_by_fold(folds):
    by_fold = folds.groupby(["origin", "model"], as_index=False)["median_abs_log_error"].mean()
    return by_fold.pivot(index="origin", columns="model", values="median_abs_log_error")


def label_positions(ends, gap):
    """Nudge end labels apart so lines that finish close together stay readable."""
    placed = {}
    for model, y in sorted(ends.items(), key=lambda kv: kv[1]):
        low = max(placed.values()) + gap if placed else y
        placed[model] = max(y, low)
    return placed


def plot(pivot, out):
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    x = pd.to_datetime(pivot.index)
    models = [m for m in MODELS if m in pivot]
    for model in models:
        label, color, marker = MODELS[model]
        ax.plot(x, pivot[model], color=color, lw=2, marker=marker, ms=6, label=label,
                markeredgecolor="#fcfcfb", markeredgewidth=1.5)
    ax.set_ylim(bottom=0, top=pivot[models].to_numpy().max() * 1.1)
    ends = {m: pivot[m].iloc[-1] for m in models}
    for model, y in label_positions(ends, gap=ax.get_ylim()[1] * 0.05).items():
        ax.annotate(f"{MODELS[model][0]} {ends[model]:.2f}", (x[-1], y), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=9, color=INK)
    ax.set_xticks(x)
    ax.set_ylabel("Median |log error|, lower is better", color=MUTED)
    ax.set_title("Forecast error for each monthly backtest origin", loc="left", color=INK)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %Y"))
    ax.grid(axis="y", color="#e6e5e0", lw=0.8)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c8c7c0")
    ax.tick_params(colors=MUTED, length=0)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.1), ncol=4, fontsize=9)
    fig.tight_layout()
    fig.savefig(out, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folds", type=Path, default=Path("results/backtest_point_folds.csv"))
    parser.add_argument("--out", type=Path, default=Path("results/backtest_error.png"))
    args = parser.parse_args()
    plot(error_by_fold(pd.read_csv(args.folds)), args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
