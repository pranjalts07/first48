from first48.wiki import is_promotion, to_record


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
