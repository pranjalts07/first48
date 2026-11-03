import datetime as dt

from first48 import content


def test_day_ends():
    end_d0, end_d1 = content.day_ends(dt.date(2026, 1, 15))
    assert content.stamp(end_d0) == "2026-01-15T23:59:59Z"
    assert content.stamp(end_d1) == "2026-01-16T23:59:59Z"


def test_plain_text_drops_markup():
    wikitext = "{{Infobox x|a=1}}'''Alpha''' is a [[river|stream]] in Ruritania.<ref>src</ref>"
    assert content.plain_text(wikitext) == "Alpha is a stream in Ruritania."


def test_revisions_pick_latest_before_each_day_end(monkeypatch):
    revs = [
        {"revid": 3, "timestamp": "2026-01-16T10:00:00Z", "size": 300},
        {"revid": 2, "timestamp": "2026-01-15T20:00:00Z", "size": 200},
        {"revid": 1, "timestamp": "2026-01-15T08:00:00Z", "size": 100},
    ]
    monkeypatch.setattr(content, "get_json", lambda *a, **k: {"query": {"pages": [{"revisions": revs}]}})
    end_d0, end_d1 = content.day_ends(dt.date(2026, 1, 15))
    at_d0, at_d1 = content.revisions_before(1, end_d0, end_d1, session=None)
    assert (at_d0["revid"], at_d1["revid"]) == (2, 3)
