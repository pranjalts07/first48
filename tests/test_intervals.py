import numpy as np

from first48.intervals import conformal_margin


def test_margin_is_zero_when_band_just_fits():
    actual = np.arange(10.0)
    assert conformal_margin(actual, actual, actual) == 0


def test_margin_widens_a_band_that_is_too_narrow():
    rng = np.random.default_rng(0)
    actual = rng.normal(size=2000)
    margin = conformal_margin(np.full(2000, -0.5), np.full(2000, 0.5), actual)
    covered = np.mean(np.abs(actual) <= 0.5 + margin)
    assert margin > 0
    assert 0.79 <= covered <= 0.82


def test_margin_narrows_a_band_that_is_too_wide():
    actual = np.random.default_rng(0).normal(size=2000)
    assert conformal_margin(np.full(2000, -5.0), np.full(2000, 5.0), actual) < 0
