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
