"""苏格拉底引导式对话编排：检索 -> 拼装 Prompt -> 流式生成。"""
from app.agents.prompts import (
    CODE_DIAGNOSIS_SYSTEM,
    SOCRATIC_SYSTEM,
    build_context,
)
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


def answer_stream(question: str, history: list[dict] | None = None):
    """普通苏格拉底对话：检索相关知识后流式生成引导性回复。"""
    history = history or []
    retrieved = rag.search(question)
    messages = _build_chat_messages(question, history, retrieved)
    yield from chat_stream(messages)


def analyze_code_stream(code: str, language: str = "cpp", question: str | None = None):
    """代码剖析：bug 库加权检索 + 静态线索 + 流式诊断引导。"""
    query = (question or "") + "\n" + code

    # bug 库优先（代码 debug 场景 bug 案例最相关），讲义补充
    bugs = rag.search(query, categories=["buglib"], top_k=2)
    lectures = rag.search(query, categories=["lecture", "solutions"], top_k=2)
    retrieved = sorted(bugs + lectures, key=lambda x: x["distance"])[:4]

    context = build_context(retrieved)
    system = CODE_DIAGNOSIS_SYSTEM
    if context:
        system += "\n\n" + context

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
    yield from chat_stream(messages)
