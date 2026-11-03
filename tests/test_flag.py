import numpy as np
import pandas as pd

from first48.flag import top_share
from first48.metrics import average_precision, precision_at_recall


def test_top_share_per_group():
    values = pd.Series(range(40))
    groups = pd.Series(["a"] * 20 + ["b"] * 20)
    flags = top_share(values, groups)
    assert list(values[flags]) == [19, 39]


def test_top_share_flags_at_least_one():
    assert top_share(pd.Series([1, 5, 3]), pd.Series(["a"] * 3)).sum() == 1


def test_average_precision_perfect_and_worst():
    labels = [1, 1, 0, 0]
    assert average_precision(labels, [4, 3, 2, 1]) == 1
    assert np.isclose(average_precision(labels, [1, 2, 3, 4]), (1 / 3 + 2 / 4) / 2)


def test_precision_at_recall():
    labels = [1, 0, 1, 0]
    scores = [4, 3, 2, 1]
    assert precision_at_recall(labels, scores, 0.5) == 1
    assert np.isclose(precision_at_recall(labels, scores, 1.0), 2 / 3)
