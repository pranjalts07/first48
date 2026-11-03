import numpy as np

from first48.metrics import interval_metrics, paired_bootstrap, pinball, point_metrics


def test_perfect_forecast_has_zero_error():
    m = point_metrics([10, 0, 500], [10, 0, 500])
    assert m["median_abs_log_error"] == 0
    assert m["smape"] == 0


def test_log_error_is_symmetric_in_ratio():
    over = point_metrics([199], [99])["median_abs_log_error"]
    under = point_metrics([49], [99])["median_abs_log_error"]
    assert np.isclose(over, under)


def test_mape_skips_zero_actuals():
    assert point_metrics([5, 20], [0, 10])["mape"] == 100


def test_pinball_penalizes_underprediction_more_at_high_quantile():
    assert pinball([0], [9], 0.9) > pinball([99], [9], 0.9)


def test_interval_coverage():
    m = interval_metrics([0, 10], [10, 20], [5, 30])
    assert m["coverage"] == 0.5


def test_bootstrap_interval_contains_estimate():
    rng = np.random.default_rng(1)
    a, b = rng.random(300) + 0.2, rng.random(300)
    est, lo, hi = paired_bootstrap(a, b, n_boot=200)
    assert lo < est < hi
    assert lo > 0


def test_mde_shrinks_with_sample_size():
    from first48.power import mde

    assert np.isclose(mde(1.0, 100), 0.396, atol=0.001)
    assert mde(1.0, 400) < mde(1.0, 100)
