import numpy as np
import pandas as pd

from first48.shadow import alerts, psi, reference


def test_psi_is_near_zero_for_same_distribution():
    rng = np.random.default_rng(0)
    ref = reference(rng.normal(size=5000))
    assert psi(ref["share"], rng.normal(size=5000), ref["edges"]) < 0.02


def test_psi_flags_a_shift():
    rng = np.random.default_rng(0)
    ref = reference(rng.normal(size=5000))
    assert psi(ref["share"], rng.normal(loc=1, size=5000), ref["edges"]) > 0.25


def test_alerts():
    monitoring = pd.DataFrame({"cohort_date": ["a", "b"], "psi_log_d1": [0.01, 0.4], "psi_log_pred": [0.01, 0.01]})
    scores = pd.DataFrame({"cohort_date": ["a"], "coverage": [0.6]})
    lines = alerts(monitoring, scores)
    assert len(lines) == 2
    assert lines[0].startswith("b: input drift")


def test_saved_model_predicts_live_rows_with_edit_activity(tmp_path):
    import datetime as dt

    from first48.shadow import predict, train
    from tests.test_backtest import articles

    history = articles(dt.date(2026, 1, 1), 40).assign(edits_d0=3, edits_48h=5, editors_48h=2,
                                                       size_d0=2000, size_d1=2500)
    train(history, tmp_path)
    live = history[history["cohort_date"] == history["cohort_date"].max()].drop(columns="views_30d")
    out = predict(live, tmp_path)
    assert len(out) == len(live)
    assert (out["lower"] <= out["upper"]).all()
