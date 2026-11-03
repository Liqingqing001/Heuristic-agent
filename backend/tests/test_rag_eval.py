"""检索评测必须按文档去重，不能用重复分块虚增召回率。"""
from scripts.eval_rag import evaluate_case, evaluate, expected_keys, percentile


def test_kp_source_and_id_are_one_document():
    case = {"id": "a", "query": "链表", "relevant_kp_ids": ["ds-01-02"], "relevant_sources": ["ds-01-02-单链表插入与删除.md", "03-链表断链.md"]}
    assert len(expected_keys(case)) == 2
    results = [{"kp_id": "ds-01-02", "source": "ds-01-02-单链表插入与删除.md"}] * 3
    measured = evaluate_case(case, results, 3)
    assert measured["recall"] == .5
    assert measured["reciprocal_rank"] == 1


def test_rank_and_cutoff():
    case = {"id": "a", "query": "链表", "relevant_kp_ids": ["ds-01-02"], "relevant_sources": []}
    results = [{"kp_id": "ds-02-01"}, {"kp_id": "ds-01-02"}]
    assert evaluate_case(case, results, 1)["hit"] is False
    assert evaluate_case(case, results, 3)["reciprocal_rank"] == .5
    assert evaluate_case(case, results, 3)["returned_precision"] == .5


def test_unanswerable_and_mode_are_reported():
    cases = [{"id": "a", "query": "天气", "relevant_kp_ids": [], "relevant_sources": []}]
    def search(query, **kwargs):
        assert kwargs == {"top_k": 3, "mode": "lexical", "audience": "hint"}
        return []
    report = evaluate(cases, search, "lexical", 3)
    assert report["metrics"]["no_answer_accuracy"] == 1
    assert report["metrics"]["hit_at_k"] is None
    assert report["cases"][0]["correct_abstention"] is True
    assert report["audience"] == "hint"


def test_percentile_interpolates_small_sample():
    assert percentile([10], .95) == 10
    assert percentile([0, 100], .5) == 50
    assert percentile([], .95) == 0


def test_bundled_labels_reference_existing_course_documents():
    from pathlib import Path
    from scripts.eval_rag import load_cases, DEFAULT_DATASET
    cases = load_cases(DEFAULT_DATASET)
    knowledge = DEFAULT_DATASET.parent / 'knowledge'
    known_sources = {path.name for path in knowledge.rglob('*.md')}
    known_kps = {path.name[:8] for path in (knowledge / 'kp').glob('ds-*.md')}
    assert len(cases) >= 25
    assert any(not expected_keys(case) for case in cases)
    for case in cases:
        assert set(case['relevant_sources']) <= known_sources
        assert set(case['relevant_kp_ids']) <= known_kps
