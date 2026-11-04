import pandas as pd

from first48.chart import error_by_fold, label_positions, plot


def folds():
    rows = []
    for origin in ["2026-03-01", "2026-04-01"]:
        for model, err in [("flat_rate", 0.9), ("szabo_huberman_log", 0.7), ("log_linear", 0.6)]:
            rows.append({"origin": origin, "model": model, "seed": None, "median_abs_log_error": err})
        for seed, err in enumerate([0.4, 0.5]):
            rows.append({"origin": origin, "model": "lightgbm", "seed": seed, "median_abs_log_error": err})
    return pd.DataFrame(rows)


def test_seeds_are_averaged_within_a_fold():
    pivot = error_by_fold(folds())
    assert pivot.loc["2026-03-01", "lightgbm"] == 0.45
    assert pivot.loc["2026-03-01", "flat_rate"] == 0.9


def test_plot_writes_a_png(tmp_path):
    out = tmp_path / "chart.png"
    plot(error_by_fold(folds()), out)
    assert out.read_bytes()[:4] == b"\x89PNG"


def test_close_end_labels_are_spread_apart():
    placed = label_positions({"a": 0.50, "b": 0.51, "c": 0.9}, gap=0.05)
    assert placed["b"] - placed["a"] >= 0.05
    assert placed["c"] == 0.9
