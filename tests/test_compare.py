import datetime as dt

import numpy as np
import pandas as pd

from first48.compare import with_embeddings


def test_only_2026_cohorts_get_text(tmp_path):
    articles = pd.DataFrame({"page_id": [1, 2], "cohort_date": [dt.date(2025, 6, 1), dt.date(2026, 2, 1)]})
    emb = pd.DataFrame({"page_id": [1, 2], "emb_d0": [np.ones(3), np.ones(3)], "emb_d1": [np.ones(3), None]})
    emb.to_parquet(tmp_path / "emb.parquet")
    df = with_embeddings(articles, tmp_path / "emb.parquet")
    assert df["page_id"].tolist() == [2]
    assert np.isnan(df["emb_d1"].iloc[0]).all()
