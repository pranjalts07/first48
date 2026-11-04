"""Point forecasts of 30-day views from day 0 and day 1 views.

Each model has fit(train) and predict(test), where both are rows of
fct_articles, and predicts views (not log views).
"""
import lightgbm as lgb
import numpy as np
import pandas as pd

ARTICLE_TYPES = ["person", "film_tv", "sports_event", "place", "organization", "other"]
EDIT_COLUMNS = ["edits_d0", "edits_48h", "editors_48h", "size_d0", "size_d1"]


def features(df, edits=False):
    t0 = pd.to_datetime(df["t0"])
    out = pd.DataFrame({
        "log_d0": np.log1p(df["views_d0"]),
        "log_d1": np.log1p(df["views_d1"]),
        "hours_day0": 24 - t0.dt.hour - t0.dt.minute / 60,
        "weekday": df["weekday"],
        "is_move": (df["source"] == "move").astype(int),
        "article_type": pd.Categorical(df["article_type"], categories=ARTICLE_TYPES),
    }, index=df.index)
    if edits:
        # Missing edit history stays missing; LightGBM learns a direction for it.
        for col in EDIT_COLUMNS:
            values = df[col] if col in df else pd.Series(np.nan, index=df.index)
            out[f"log_{col}"] = np.log1p(values.astype(float))
    return out


class FlatRate:
    """Day 1 views continue for the remaining 28 days."""

    def fit(self, train):
        return self

    def predict(self, test):
        return (test["views_48h"] + 28 * test["views_d1"]).to_numpy(dtype=float)


class SzaboHuberman:
    """log Y = log(day 0 + day 1 views) + b, slope fixed at 1.

    Converting back multiplies by exp(s^2 / 2), the lognormal mean correction.
    """

    def fit(self, train):
        resid = np.log1p(train["views_30d"]) - np.log1p(train["views_48h"])
        self.b = resid.mean()
        self.var = resid.var()
        return self

    def predict(self, test):
        return np.expm1(np.log1p(test["views_48h"]) + self.b + self.var / 2).to_numpy()


class LogLinear:
    """log Y on log early views with a free slope, plus creation hour effects."""

    def design(self, df):
        hours = pd.get_dummies(pd.Categorical(df["creation_hour"], categories=range(24)), drop_first=True)
        return np.column_stack([np.ones(len(df)), np.log1p(df["views_48h"]), hours.to_numpy(dtype=float)])

    def fit(self, train):
        self.coef, *_ = np.linalg.lstsq(self.design(train), np.log1p(train["views_30d"]), rcond=None)
        return self

    def predict(self, test):
        return np.expm1(self.design(test) @ self.coef)


class GradientBoosting:
    """LightGBM on log views. alpha=None fits the median with an L1 loss."""

    def __init__(self, seed=0, alpha=None, n_estimators=400, edits=True):
        self.edits = edits
        objective = {"objective": "quantile", "alpha": alpha} if alpha else {"objective": "l1"}
        self.model = lgb.LGBMRegressor(
            n_estimators=n_estimators,
            learning_rate=0.05,
            num_leaves=31,
            min_child_samples=50,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            random_state=seed,
            verbose=-1,
            **objective,
        )

    def matrix(self, df):
        return features(df, edits=self.edits)

    def fit(self, train):
        self.model.fit(self.matrix(train), np.log1p(train["views_30d"]))
        return self

    def predict(self, test):
        return np.expm1(self.model.predict(self.matrix(test))).clip(min=0)


class ContentGradientBoosting(GradientBoosting):
    """LightGBM on a text embedding and article type, optionally with the early-view features.

    Expects an emb_d0 or emb_d1 column holding one vector per article.
    """

    def __init__(self, text_day, with_views, seed=0):
        super().__init__(seed=seed, edits=False)
        self.text_day = text_day
        self.with_views = with_views

    def matrix(self, df):
        emb = pd.DataFrame(np.vstack(df[f"emb_{self.text_day}"].to_numpy()), index=df.index).add_prefix("emb_")
        if self.with_views:
            base = features(df)
        else:
            base = pd.DataFrame({"article_type": pd.Categorical(df["article_type"], categories=ARTICLE_TYPES)},
                                index=df.index)
        return pd.concat([base, emb], axis=1)
