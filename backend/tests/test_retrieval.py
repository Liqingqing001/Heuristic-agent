"""无需模型的检索排序回归。"""
from app.core import retrieval


def chunk(identifier, text, title="", section="", document=None, category="lecture", **extra):
    return {"chunk_id": identifier, "document_id": document or identifier, "content_hash": identifier + text,
            "text": text, "title": title, "section": section, "category": category, **extra}


def test_title_and_heading_receive_explicit_boost():
    docs = [chunk("body", "反转链表的方法与边界条件。"),
            chunk("heading", "思考指针指向变化。", section="反转链表"),
            chunk("title", "思考指针指向变化。", title="反转链表")]
    ranked = retrieval.lexical_rank("反转链表", docs)
    assert [r["chunk_id"] for r in ranked] == ["title", "heading", "body"]
    assert all(r["lexical_score"] > 0 and 0 <= r["relevance"] <= 1 for r in ranked)


def test_bigrams_do_not_cross_punctuation():
    assert "zh:表反" not in retrieval.tokenize("链表，反转")
    assert "zh:表反" in retrieval.tokenize("链表反转")


def test_code_symbols_and_identifier_query():
    docs = [chunk("pointer", "先保存 p -> next，再改变指向。"), chunk("other", "二叉树的左右子树递归遍历。")]
    ranked = retrieval.lexical_rank("p->next", docs)
    assert [r["chunk_id"] for r in ranked] == ["pointer"]
    assert "code:p->next" in retrieval.tokenize("p -> next")


def test_aliases_match_chinese_titles_for_ascii_queries():
    docs = [chunk("bst", "左子树小于根，右子树大于根。", title="二叉排序树"),
            chunk("dfs", "使用递归和栈遍历图。", title="深度优先遍历"),
            chunk("other", "使用队列访问相邻顶点。", title="广度优先遍历")]
    assert retrieval.lexical_rank("BST", docs)[0]["chunk_id"] == "bst"
    assert retrieval.lexical_rank("DFS", docs)[0]["chunk_id"] == "dfs"
    assert "bst" not in retrieval.expand_query("mybstvariable").split()


def test_no_forced_hits_and_weak_overlap_rejected():
    docs = [chunk("one", "二叉树遍历以及左右子树。", title="二叉树")]
    assert retrieval.lexical_rank("北京今天会下雨吗", docs) == []
    assert retrieval.lexical_rank("如何准备面试", docs) == []
    assert retrieval.lexical_rank("二叉香蕉面包", docs) == []
    assert retrieval.lexical_rank("", docs) == []
    assert retrieval.lexical_rank("二叉树", docs, limit=0) == []


def test_short_domain_query_remains_usable():
    assert retrieval.lexical_rank("栈", [chunk("stack", "先进后出。", title="顺序栈与链栈")])


def test_cache_invalidates_title_changes_even_with_same_content_hash():
    docs = [chunk("a", "保存 next 指针。", title="反转链表")]
    assert retrieval.lexical_rank("反转链表", docs)
    changed = [{**docs[0], "title": "循环队列"}]
    assert retrieval.lexical_rank("反转链表", changed) == []


def test_rrf_combines_rank_not_raw_score_preserves_metadata_and_deduplicates():
    a = chunk("a", "链表", lexical_score=999999, relevance=0.8)
    b = chunk("b", "二叉树", lexical_score=0.1)
    c = chunk("c", "哈希表")
    result = retrieval.rrf([[a, b, a], [b, c]])
    assert [r["chunk_id"] for r in result] == ["b", "a", "c"]
    assert result[0]["retrieval"] == "hybrid"
    assert result[0]["lexical_score"] == 0.1
    assert next(r for r in result if r["chunk_id"] == "a")["relevance"] == 0.8
    assert all(0 <= r["distance"] <= 1 for r in result)
    assert retrieval.rrf([], 4) == []


def test_category_quotas_and_document_diversity_keep_original_order():
    docs = [chunk("l1", "a", document="lecture"), chunk("l2", "a", document="lecture"),
            chunk("l3", "a", document="lecture"), chunk("b1", "a", category="buglib"),
            chunk("k1", "a", category="kp"), chunk("k2", "a", category="kp")]
    selected = retrieval.select_diverse(docs, 4, per_document=2, quotas={"kp": 1, "buglib": 1})
    assert [r["chunk_id"] for r in selected] == ["l1", "l2", "b1", "k1"]
    assert len(retrieval.select_diverse(docs, 10, per_document=1)) == 4
    assert retrieval.select_diverse(docs, 0) == []


def test_missing_quota_does_not_prevent_filling_and_duplicate_ids_not_emitted():
    docs = [chunk("a", "a"), chunk("a", "a"), chunk("b", "b")]
    assert len(retrieval.select_diverse(docs, 3, quotas={"kp": 1})) == 2
