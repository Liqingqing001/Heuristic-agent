"""检索编排回归：不下载向量模型，不调用外部大模型。"""
from app.agents import prompts, socratic
from app.core.corpus import estimate_tokens


def chunk(identifier="part-1", **extra):
    return {
        "chunk_id": identifier, "document_id": "lecture/tree.md", "source": "tree.md",
        "category": "lecture", "section": "递归", "title": "树的遍历",
        "text": "先检查递归的终止条件，再思考子树的处理顺序。", "audience": "hint",
        "index_version": "test-version", **extra,
    }


def test_followup_uses_recent_student_context_only():
    history = [
        {"role": "user", "content": "单链表插入时指针更新顺序是什么？"},
        {"role": "assistant", "content": "错误的助手建议不要用于检索扩写"},
    ]
    query = socratic.build_retrieval_query("这里为什么会断？", history)
    assert "单链表插入" in query
    assert "这里为什么会断" in query
    assert "助手建议" not in query
    assert socratic.build_retrieval_query("解释二分查找的边界", history) == "解释二分查找的边界"
    assert socratic.build_retrieval_query("法国首都？", history) == "法国首都？"


def test_context_budget_uses_whole_safe_chunks_and_consistent_references():
    results = [chunk("too-big", text="树" * 4000), chunk("safe"), chunk("solution", audience="solution")]
    selected = prompts.select_context(results, max_tokens=220)
    assert [item["chunk_id"] for item in selected] == ["safe"]
    context = prompts.build_context(results, max_tokens=220)
    assert estimate_tokens(context) <= 220
    assert "先检查递归" in context
    assert "solution" not in context
    assert socratic._references(selected)[0]["chunk_id"] == "safe"
    assert "未检索到足够相关" in prompts.build_context([])


def test_reference_and_context_cover_non_kp_sources(monkeypatch):
    received = {}
    results = [chunk(), chunk("unsafe", audience="solution")]
    monkeypatch.setattr(socratic.rag, "search", lambda query, **kwargs: results)
    def stream(messages, **kwargs):
        received["messages"] = messages
        yield "你认为应该先检查什么？"
    monkeypatch.setattr(socratic, "chat_stream", stream)
    events = list(socratic.answer_stream("递归为什么无限调用？"))
    references = events[0][1]
    assert len(references) == 1
    assert references[0]["source"] == "tree.md"
    assert references[0]["index_version"] == "test-version"
    assert references[0]["kp_id"] is None
    assert "先检查递归" in received["messages"][0]["content"]
    assert events[1][0] == "token"


def test_history_bounded_and_latest_question_preserved():
    history = [
        {"role": "user", "content": "旧" * 3000},
        {"role": "assistant", "content": "最近的引导"},
        {"role": "user", "content": "最近的问题"},
    ]
    question = "学生当前问题，不应截断"
    messages = socratic._build_chat_messages(question, history, [])
    assert len(messages) == 4
    assert messages[-1] == {"role": "user", "content": question}
    assert messages[1]["content"] == "最近的引导"
    assert sum(estimate_tokens(item["content"]) for item in messages[1:-1]) < 2000


def test_code_query_and_retrieval_only_once_with_evidence_bound_diagnosis(monkeypatch):
    calls = []
    actual_analyze = socratic.code_parser.analyze
    analyses = []
    def analyze(code):
        analyses.append(code)
        return actual_analyze(code)
    def search(query, **kwargs):
        calls.append((query, kwargs))
        return [chunk(kp_id="ds-01-02", category="kp")]
    monkeypatch.setattr(socratic.code_parser, "analyze", analyze)
    monkeypatch.setattr(socratic.rag, "search", search)
    monkeypatch.setattr(socratic, "chat_stream", lambda *args, **kwargs: iter([
        '请检查指针更新顺序。\n<<<DIAG\n{"error_types":["断链"],"kp_ids":["ds-01-02","ds-99-99"],"severity":"medium","hint_level_reached":1,"next_question":"原后继指向谁？"}\nDIAG>>>'
    ]))
    code = "void insert(Node* p, Node* q) { p->next = q; q->next = p->next; }\n" + "// extra\n" * 3000
    events = list(socratic.analyze_code_stream(code, question="为什么会断链？"))
    assert len(calls) == len(analyses) == 1
    query, options = calls[0]
    assert len(query) <= 1800
    assert "链表" in query and "指针顺序" in query
    assert options["quotas"] == {"kp": 2, "buglib": 1}
    assert "solutions" not in options["categories"]
    assert options["audience"] == "hint"
    assert events[-1][0] == "diagnosis"
    assert events[-1][1]["kp_ids"] == ["ds-01-02"]


def test_code_context_reserves_kp_and_bug_before_budget_fill(monkeypatch):
    # 最相关的三个讲义先占满预算，Bug 排名最后；配额应仍然进入模型上下文。
    results = [chunk(f"lecture-{i}", text="讲" * 350) for i in range(3)] + [
        chunk("kp-a", category="kp", kp_id="ds-01-02", text="甲" * 350),
        chunk("kp-b", category="kp", kp_id="ds-01-03", text="乙" * 350),
        chunk("bug-last", category="buglib", text="错" * 350),
    ]
    selected = socratic._select_code_context(results)
    ids = [item["chunk_id"] for item in selected]
    assert ids[:3] == ["kp-a", "kp-b", "bug-last"]
    assert len(selected) < 6
    assert ids[3:] == [item["chunk_id"] for item in results[:len(ids) - 3]]
    context = prompts.build_context(selected)
    assert estimate_tokens(context) <= 1800
    refs = socratic._references(selected)
    assert [reference["chunk_id"] for reference in refs] == ids
    for reference in refs:
        assert reference["chunk_id"] in context
    assert "lecture-2" not in context
    captured = {}
    monkeypatch.setattr(socratic.rag, "search", lambda *args, **kwargs: results)
    def stream(messages, **kwargs):
        captured["system"] = messages[0]["content"]
        yield "先检查哪个指针？"
    monkeypatch.setattr(socratic, "chat_stream", stream)
    list(socratic.analyze_code_stream("p->next = q;"))
    evidence = captured["system"].split("<course_evidence>", 1)[1].split("</course_evidence>", 1)[0]
    assert "bug-last" in evidence
    assert "kp-a" in evidence and "kp-b" in evidence
    assert estimate_tokens("<course_evidence>" + evidence + "</course_evidence>") <= 1800
