"""苏格拉底引导式对话编排：检索 -> 拼装 Prompt -> 流式生成。"""
from __future__ import annotations

from app.agents import diagnosis as diagnosis_parser
from app.agents.prompts import (
    CODE_DIAGNOSIS_SYSTEM,
    SOCRATIC_SYSTEM,
    build_context,
    build_diagnosis_protocol,
)
from app.agents.stream_filter import DiagnosisStreamFilter
from app.core import rag
from app.core.llm import chat_stream
from app.utils import code_parser


def _build_chat_messages(question: str, history: list[dict], retrieved: list[dict]) -> list[dict]:
    context = build_context(retrieved)
    system = SOCRATIC_SYSTEM
    if context:
        system += "\n\n" + context

    messages: list[dict] = [{"role": "system", "content": system}]
    for msg in history:
        role = msg.get("role")
        content = msg.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})
    return messages


def answer_stream(question: str, history: list[dict] | None = None, api_key: str | None = None):
    """普通苏格拉底对话：检索相关知识后流式生成引导性回复。

    产出 ``("references", [...])`` 一次，随后是 ``("token", 文本)``。
    """
    history = history or []
    retrieved = rag.search(question)

    references: list[dict] = []
    seen: set[str] = set()
    for item in retrieved:
        kp_id = item.get("kp_id")
        if not kp_id or kp_id in seen:
            continue
        seen.add(kp_id)
        references.append({
            "kp_id": kp_id,
            "title": item.get("title") or "",
            "chapter": item.get("chapter"),
            "category": item.get("category"),
        })

    messages = _build_chat_messages(question, history, retrieved)
    yield ("references", references)
    for token in chat_stream(messages, api_key=api_key):
        yield ("token", token)


def analyze_code_stream(
    code: str,
    language: str = "cpp",
    question: str | None = None,
    api_key: str | None = None,
):
    """代码剖析：知识点 + bug 库加权检索 + 静态线索 + 结构化诊断。

    产出 ``("token", 文本)`` 若干次，最后产出 ``("diagnosis", dict)``。
    """
    query = (question or "") + "\n" + code

    # 知识点优先（统计掌握度要用），bug 库补充案例，讲义兜底
    kps = rag.search(query, categories=[rag.KP_COLLECTION], top_k=3)
    bugs = rag.search(query, categories=["buglib"], top_k=2)
    lectures = rag.search(query, categories=["lecture", "solutions"], top_k=2)
    retrieved = sorted(kps + bugs + lectures, key=lambda item: item["distance"])[:6]

    context = build_context(retrieved)
    system = CODE_DIAGNOSIS_SYSTEM
    if context:
        system += "\n\n" + context
    kp_ids = [item["kp_id"] for item in retrieved if item.get("kp_id")]
    system += "\n\n" + build_diagnosis_protocol(kp_ids)

    clues = code_parser.analyze(code)

    user_content = f"学生提交的代码（{language}）：\n```{language}\n{code}\n```\n"
    if clues:
        lines = ["\n代码静态分析线索（供你参考定位，不要照搬，也不要给出完整修复代码）："]
        for kind, items in clues.items():
            lines.append(f"- {kind}：{'; '.join(items)}")
        user_content += "\n".join(lines) + "\n"
    if question:
        user_content += f"\n学生的问题：{question}\n"
    user_content += "\n请先诊断问题，再以提问引导学生自己修复，不要给出完整代码。"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    splitter = DiagnosisStreamFilter()
    for chunk in chat_stream(messages, api_key=api_key, temperature=0.4):
        visible = splitter.feed(chunk)
        if visible:
            yield ("token", visible)

    tail, payload = splitter.finish()
    if tail:
        yield ("token", tail)

    parsed = diagnosis_parser.parse(payload)
    if parsed is None:
        parsed = diagnosis_parser.heuristic(code, clues)
    yield ("diagnosis", parsed)
