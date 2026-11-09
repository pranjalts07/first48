import pandas as pd

from first48 import results
from first48.backtest import BASELINES


def test_yoy_section_reports_the_cost_of_not_retraining(tmp_path, monkeypatch):
    monkeypatch.setattr(results, "R", tmp_path)
    pd.DataFrame({"month": ["2026-01", "2026-02"], "articles": [100, 200], "trained_on_2025": [0.5, 0.6],
                  "retrained_monthly": [0.4, 0.4], "flat_rate": [1.0, 1.0]}).to_csv(tmp_path / "yoy.csv", index=False)
    lines = results.yoy_section()
    assert "| 2026-02 | 200 | 0.600 | 0.400 | 1.000 |" in lines
    assert lines[-1] == "Mean cost of not retraining: 0.150."


def test_dyk_section_has_a_row_per_model(tmp_path, monkeypatch):
    monkeypatch.setattr(results, "R", tmp_path)
    models = [*BASELINES, "lightgbm_no_edits", "lightgbm"]
    rows = [{"model": m, "featured": f, "n": 10 if f else 90, "median_abs_log_error": 2.0 if f else 0.5}
            for m in models for f in (True, False)]
    pd.DataFrame(rows).to_csv(tmp_path / "dyk_errors.csv", index=False)
    lines = results.dyk_section()
    assert "| Model | Featured (10) | Not featured (90) |" in lines
    assert "| lightgbm | 2.000 | 0.500 |" in lines


def test_power_section(tmp_path, monkeypatch):
    monkeypatch.setattr(results, "R", tmp_path)
    pd.DataFrame({"weeks": [2], "flagged_per_arm": [192], "mde_log": [0.43], "mde_log_adjusted": [0.276],
                  "mde_pct_adjusted": [31.77]}).to_csv(tmp_path / "experiment_power.csv", index=False)
    assert results.power_section()[-1] == "| 2 | 192 | 0.430 | 0.276 | 31.8% |"


def test_criteria_section_reports_a_missed_interval_target(tmp_path, monkeypatch):
    monkeypatch.setattr(results, "R", tmp_path)
    (tmp_path / "holdout").mkdir()
    rows = [{"origin": o, "model": m, "median_abs_log_error": 0.4 if m == "lightgbm" else 0.6}
            for o in ["2026-03-01", "2026-04-01"] for m in [*BASELINES, "lightgbm"]]
    pd.DataFrame(rows).to_csv(tmp_path / "backtest_point_folds.csv", index=False)
    pd.DataFrame({"baseline": list(BASELINES), "ci_low": 0.1}).to_csv(tmp_path / "holdout" / "point_vs_baselines.csv")
    pd.DataFrame({"coverage": [0.84, 0.85]}).to_csv(tmp_path / "holdout" / "intervals.csv")
    pd.DataFrame({"model_precision_at_baseline_recall": [0.7], "baseline_precision": [0.6]}).to_csv(
        tmp_path / "holdout" / "flag.csv")
    lines = results.criteria_section()
    assert lines[4].endswith("| met |")
    assert "wins 2 of 2 folds" in lines[4]
    assert lines[5] == "| Intervals: 80% ranges cover 77% to 83% of holdout articles | 84.5% | missed |"
    assert lines[6].endswith("| met |")


def test_horizons_section_counts_folds_that_improve(tmp_path, monkeypatch):
    monkeypatch.setattr(results, "R", tmp_path)
    rows = [{"origin": o, "forecast_day": d, "pinto_style": 0.6 / d, "lightgbm": err}
            for o, errs in [("2026-03-01", [0.4, 0.3, 0.2]), ("2026-04-01", [0.4, 0.5, 0.2])]
            for d, err in zip([2, 4, 8], errs)]
    pd.DataFrame(rows).to_csv(tmp_path / "horizons.csv", index=False)
    pd.DataFrame({"forecast_day": [2, 4, 8], "median_share_seen": [0.3, 0.4, 0.5]}).to_csv(
        tmp_path / "horizons_share.csv", index=False)
    lines = results.horizons_section()
    assert lines[-3] == "| day 1 | 30.0% | 0.300 | 0.400 |  |"
    assert lines[-2] == "| day 3 | 40.0% | 0.150 | 0.400 | 1 of 2 |"
    assert lines[-1] == "| day 7 | 50.0% | 0.075 | 0.200 | 2 of 2 |"
