import json

from first48.warehouse import build


def write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def page(page_id, title, t0, source="create"):
    return {"page_id": page_id, "title": title, "t0": t0, "source": source, "fetched_at": "2026-11-02T00:00:00Z"}


def state(page_id, title, redirect=False, types=()):
    return {
        "page_id": page_id, "taken_at": "2026-11-02T00:00:00Z", "exists": True, "namespace": 0,
        "is_redirect": redirect, "title": title, "last_rev_id": 1, "wikidata_item": "Q1" if types else None,
        "instance_of": list(types),
    }


def build_small(tmp_path):
    folder = tmp_path / "backfill"
    folder.mkdir()
    write(folder / "new_pages_2026-01-01.jsonl", [
        page(1, "Alpha", "2026-01-01T05:00:00Z"),
        page(2, "Beta", "2026-01-01T07:00:00Z"),
        page(3, "Gamma", "2026-01-01T22:30:00Z", "move"),
        page(3, "Gamma", "2026-01-01T23:10:00Z", "move"),
    ])
    write(folder / "snapshot_2026-01-01.jsonl", [
        state(1, "Alpha", types=["Q5", "Q11424"]),
        state(2, "Beta", redirect=True),
        state(3, "Gamma (band)", types=["Q215380"]),
    ])
    write(folder / "views_full_2026-01-01.jsonl", [
        {"page_id": 1, "title": "Alpha", "fetched_at": "x", "views": {"2026-01-01": 10, "2026-01-02": 5, "2026-01-30": 1}},
        {"page_id": 3, "title": "Gamma (band)", "fetched_at": "x", "views": {}},
    ])
    con, failures = build(tmp_path / "test.duckdb", {"backfill": folder, "live": tmp_path / "none"})
    return con, failures


def test_data_tests_pass(tmp_path):
    _, failures = build_small(tmp_path)
    assert failures == []


def test_missing_days_count_as_zero(tmp_path):
    con, _ = build_small(tmp_path)
    row = con.execute("select views_d0, views_d1, views_30d from fct_articles where page_id = 1").fetchone()
    assert row == (10, 5, 16)
    assert con.execute("select count(*) from stg_daily_views where page_id = 1").fetchone()[0] == 30


def test_redirects_are_not_articles(tmp_path):
    con, _ = build_small(tmp_path)
    ids = [r[0] for r in con.execute("select page_id from fct_articles order by page_id").fetchall()]
    assert ids == [1, 3]


def test_first_entry_is_t0(tmp_path):
    con, _ = build_small(tmp_path)
    row = con.execute("select creation_hour, n_entries, renamed from fct_articles where page_id = 3").fetchone()
    assert row == (22, 2, True)


def test_article_type_priority(tmp_path):
    con, _ = build_small(tmp_path)
    types = dict(con.execute("select page_id, article_type from fct_articles").fetchall())
    assert types == {1: "person", 3: "organization"}


def test_cohort_still_collecting_is_not_flagged(tmp_path):
    folder = tmp_path / "backfill"
    folder.mkdir()
    write(folder / "new_pages_2026-01-01.jsonl", [page(1, "Alpha", "2026-01-01T05:00:00Z")])
    write(folder / "snapshot_2026-01-01.jsonl", [state(1, "Alpha")])
    write(folder / "views_full_2026-01-01.jsonl", [
        {"page_id": 1, "title": "Alpha", "fetched_at": "x", "views": {"2026-01-02": 3}},
    ])
    write(folder / "new_pages_2026-01-02.jsonl", [page(2, "Beta", "2026-01-02T05:00:00Z")])
    write(folder / "snapshot_2026-01-02.jsonl", [state(2, "Beta")])
    _, failures = build(tmp_path / "test.duckdb", {"backfill": folder})
    assert failures == []
