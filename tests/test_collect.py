from first48.collect import is_article


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
