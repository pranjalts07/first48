from first48.wiki import instance_of, is_promotion, page_state, to_record


def test_draft_moved_to_article_space_is_promotion():
    event = {"ns": 118, "params": {"target_ns": 0}}
    assert is_promotion(event)


def test_rename_within_article_space_is_not_promotion():
    event = {"ns": 0, "params": {"target_ns": 0}}
    assert not is_promotion(event)


def test_move_out_of_article_space_is_not_promotion():
    event = {"ns": 0, "params": {"target_ns": 118}}
    assert not is_promotion(event)


def test_record_uses_logpage_not_pageid():
    event = {"logpage": 123, "pageid": 999, "timestamp": "2026-09-01T10:00:00Z"}
    record = to_record(event, "Some title", "move")
    assert record == {
        "page_id": 123,
        "title": "Some title",
        "t0": "2026-09-01T10:00:00Z",
        "source": "move",
    }


def test_deleted_page_state():
    state = page_state({"pageid": 1, "missing": True}, "2026-11-02T06:00:00Z")
    assert state["exists"] is False
    assert state["is_redirect"] is False
    assert state["wikidata_item"] is None


def test_redirect_page_state():
    page = {"pageid": 2, "title": "Mk6 Golf", "lastrevid": 10, "redirect": True}
    state = page_state(page, "2026-11-02T06:00:00Z")
    assert state["exists"] and state["is_redirect"]


def test_article_page_state_keeps_wikidata_item():
    page = {"pageid": 3, "title": "Barbara Ireland", "lastrevid": 11,
            "pageprops": {"wikibase_item": "Q141302152"}}
    state = page_state(page, "2026-11-02T06:00:00Z")
    assert state["wikidata_item"] == "Q141302152"
    assert not state["is_redirect"]


def test_instance_of_skips_claims_without_value():
    entity = {"claims": {"P31": [
        {"mainsnak": {"datavalue": {"value": {"id": "Q5"}}}},
        {"mainsnak": {"snaktype": "somevalue"}},
    ]}}
    assert instance_of(entity) == ["Q5"]
