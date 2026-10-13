from aiops_assistant.retrieval import load_runbooks, search, tokens


def test_runbook_sections_have_stable_ids(sections):
    ids = [s.id for s in sections]
    assert len(ids) == len(set(ids))
    assert "RB:disk-full#checks" in ids
    assert all(s.category for s in sections)


def test_search_ranks_matching_runbook_first(sections):
    hits = search(sections, "write /var/lib/x: no space left on device Errno 28")
    assert hits[0][0].runbook == "disk-full"


def test_tokens_drop_stopwords():
    assert "the" not in tokens("the pool is exhausted")


def test_load_runbooks_empty_dir(tmp_path):
    assert load_runbooks(tmp_path) == []
