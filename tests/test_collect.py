from first48.collect import append_summary, is_article


def state(**changes):
    base = {"exists": True, "namespace": 0, "is_redirect": False}
    return {**base, **changes}


def test_live_article():
    assert is_article(state())


def test_redirect_is_not_article():
    assert not is_article(state(is_redirect=True))


def test_deleted_page_is_not_article():
    assert not is_article(state(exists=False, namespace=None))


def test_page_moved_back_to_draft_is_not_article():
    assert not is_article(state(namespace=118))


def test_summary_writes_header_once(tmp_path):
    path = tmp_path / "runs.csv"
    append_summary(path, {"run_date": "2026-11-03", "new_pages": 10})
    append_summary(path, {"run_date": "2026-11-04", "new_pages": 12})
    assert path.read_text().splitlines() == [
        "run_date,new_pages",
        "2026-11-03,10",
        "2026-11-04,12",
    ]
