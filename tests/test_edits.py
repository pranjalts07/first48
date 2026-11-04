import datetime as dt
import json

from first48 import edits
from first48.content import day_ends

REVS = [
    {"timestamp": "2026-01-16T18:00:00Z", "user": "B", "size": 900},
    {"timestamp": "2026-01-16T09:00:00Z", "user": "A", "size": 700},
    {"timestamp": "2026-01-15T22:00:00Z", "user": "A", "size": 500},
    {"timestamp": "2026-01-15T10:00:00Z", "userhidden": True, "size": 300},
]


def test_features_split_at_end_of_day_0():
    end_d0, _ = day_ends(dt.date(2026, 1, 15))
    f = edits.edit_features(REVS, end_d0)
    assert f == {"edits_d0": 2, "edits_48h": 4, "editors_48h": 3, "size_d0": 500, "size_d1": 900}


def test_no_revisions_gives_zero_edits():
    end_d0, _ = day_ends(dt.date(2026, 1, 15))
    f = edits.edit_features([], end_d0)
    assert (f["edits_48h"], f["size_d1"]) == (0, None)


def test_history_is_read_from_t0_to_end_of_day_1(monkeypatch):
    calls = []

    def fake_get(session, url, params):
        calls.append(dict(params))
        if len(calls) == 1:
            return {"query": {"pages": [{"revisions": REVS[:2]}]}, "continue": {"rvcontinue": "x"}}
        return {"query": {"pages": [{"revisions": REVS[2:]}]}}

    monkeypatch.setattr(edits, "get_json", fake_get)
    start = dt.datetime(2026, 1, 15, 10)
    _, end_d1 = day_ends(dt.date(2026, 1, 15))
    revs = edits.revisions_between(1, start, end_d1, session=None)
    assert len(revs) == 4
    assert calls[0]["rvstart"] == "2026-01-16T23:59:59Z"
    assert calls[0]["rvend"] == "2026-01-15T10:00:00Z"
    assert calls[1]["rvcontinue"] == "x"


def test_cohort_uses_first_entry_and_skips_non_articles(tmp_path, monkeypatch):
    cohort = dt.date(2026, 1, 15)
    pages = [
        {"page_id": 1, "t0": "2026-01-15T12:00:00Z"},
        {"page_id": 1, "t0": "2026-01-15T08:00:00Z"},
        {"page_id": 2, "t0": "2026-01-15T09:00:00Z"},
    ]
    states = [
        {"page_id": 1, "exists": True, "namespace": 0, "is_redirect": False},
        {"page_id": 2, "exists": True, "namespace": 0, "is_redirect": True},
    ]
    for name, rows in [("new_pages", pages), ("snapshot", states)]:
        (tmp_path / f"{name}_{cohort}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    starts = []
    monkeypatch.setattr(edits, "revisions_between", lambda pid, start, end, s: starts.append(start) or REVS)
    rows = edits.cohort_edits(cohort, tmp_path, session=None)
    assert [r["page_id"] for r in rows] == [1]
    assert starts == [dt.datetime(2026, 1, 15, 8)]
