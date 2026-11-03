import datetime as dt
import sys

import duckdb
import pytest

from first48 import holdout
from tests.test_backtest import articles


def make_db(path, start, days):
    df = articles(start, days)
    df["dataset"] = "backfill"
    con = duckdb.connect(str(path))
    con.execute("create table fct_articles as select * from df")
    con.close()


def run(monkeypatch, db, out):
    monkeypatch.setattr(sys, "argv", ["holdout", "--db", str(db), "--out", str(out),
                                      "--embeddings", str(db.with_name("none.parquet"))])
    holdout.main()


def test_holdout_runs_once(tmp_path, monkeypatch):
    db = tmp_path / "test.duckdb"
    make_db(db, dt.date(2026, 6, 1), 122)
    out = tmp_path / "holdout"
    run(monkeypatch, db, out)
    split = (out / "split.json").read_text()
    assert "2026-08-20 to 2026-09-30" in split
    assert "2026-06-01 to 2026-07-21" in split
    with pytest.raises(SystemExit):
        run(monkeypatch, db, out)


def test_holdout_refuses_incomplete_data(tmp_path, monkeypatch):
    db = tmp_path / "test.duckdb"
    make_db(db, dt.date(2026, 6, 1), 100)
    with pytest.raises(SystemExit):
        run(monkeypatch, db, tmp_path / "holdout")
