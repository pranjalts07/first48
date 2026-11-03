"""Forecast metrics from PLAN.md.

Log errors use log(1 + views) on both sides, because about 2% of articles
have zero views in their first 30 days and log(0) is undefined.
"""
import numpy as np


def log_error(pred, actual):
    return np.abs(np.log1p(pred) - np.log1p(actual))


def point_metrics(pred, actual):
    pred = np.asarray(pred, dtype=float)
    actual = np.asarray(actual, dtype=float)
    err = log_error(pred, actual)
    denom = np.abs(pred) + np.abs(actual)
    smape = np.where(denom == 0, 0.0, 2 * np.abs(pred - actual) / np.where(denom == 0, 1, denom))
    nonzero = actual > 0
    return {
        "median_abs_log_error": float(np.median(err)),
        "mean_abs_log_error": float(np.mean(err)),
        "smape": float(100 * np.mean(smape)),
        "summed_abs_error": float(np.sum(np.abs(pred - actual))),
        "mape": float(100 * np.mean(np.abs(pred[nonzero] - actual[nonzero]) / actual[nonzero])),
    }


def pinball(pred, actual, q):
    """Pinball loss for quantile q, on the log scale like the other errors."""
    diff = np.log1p(np.asarray(actual, dtype=float)) - np.log1p(np.asarray(pred, dtype=float))
    return float(np.mean(np.maximum(q * diff, (q - 1) * diff)))


def interval_metrics(lower, upper, actual):
    """Coverage and width of a prediction interval. Width is on the log scale."""
    lower, upper, actual = (np.asarray(a, dtype=float) for a in (lower, upper, actual))
    inside = (actual >= lower) & (actual <= upper)
    return {
        "coverage": float(np.mean(inside)),
        "mean_log_width": float(np.mean(np.log1p(upper) - np.log1p(lower))),
    }


def paired_bootstrap(err_a, err_b, stat=np.median, n_boot=2000, seed=0):
    """95% interval for stat(err_a) - stat(err_b), resampling articles in pairs."""
    err_a, err_b = np.asarray(err_a), np.asarray(err_b)
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        i = rng.integers(0, len(err_a), size=len(err_a))
        diffs.append(stat(err_a[i]) - stat(err_b[i]))
    return float(stat(err_a) - stat(err_b)), float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))


def average_precision(labels, scores):
    """Area under the precision-recall curve, as the mean precision at each true positive."""
    order = np.argsort(-np.asarray(scores, dtype=float), kind="stable")
    hits = np.asarray(labels, dtype=bool)[order]
    if not hits.any():
        return float("nan")
    precision_at_k = np.cumsum(hits) / np.arange(1, len(hits) + 1)
    return float(precision_at_k[hits].mean())


def precision_at_recall(labels, scores, recall):
    """Best precision reachable at or above a given recall when flagging the top-k scores."""
    order = np.argsort(-np.asarray(scores, dtype=float), kind="stable")
    hits = np.asarray(labels, dtype=bool)[order]
    tp = np.cumsum(hits)
    recalls = tp / hits.sum()
    precisions = tp / np.arange(1, len(hits) + 1)
    return float(precisions[recalls >= recall].max())
