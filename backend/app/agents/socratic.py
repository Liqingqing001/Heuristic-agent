"""有预算、可追溯的课程检索与苏格拉底教学编排。"""
from __future__ import annotations

import re

from app.agents import diagnosis as diagnosis_parser
from app.agents.prompts import (
    CODE_DIAGNOSIS_SYSTEM,
    SOCRATIC_SYSTEM,
    build_context,
    build_diagnosis_protocol,
    select_context,
)
from app.agents.stream_filter import DiagnosisStreamFilter
from app.core import rag
from app.core.corpus import estimate_tokens
from app.core.llm import chat_stream
from app.utils import code_parser

HISTORY_TOKEN_BUDGET = 2000
_FOLLOWUP = re.compile(r"这个|那个|这里|那里|这一步|那一步|上面|刚才|它|为什么呢|然后呢|继续|再解释|没懂|不明白")
_TOPIC = re.compile(r"链表|快慢指针|二叉|BST|AVL|栈|队列|排序|查找|哈希|散列|递归|DFS|BFS|Dijkstra|最短路径|图的|指针", re.IGNORECASE)


def build_retrieval_query(question: str, history: list[dict]) -> str:
    """仅为含指代或极短追问补上近期学生原话，不引入助手猜测。"""
    current = question.strip()[:1200]
    ambiguous = bool(_FOLLOWUP.search(current)) or bool(re.fullmatch(r"为什么[？?]?|怎么做[？?]?|怎么办[？?]?|如何处理[？?]?", current))
    if not ambiguous or _TOPIC.search(current):
        return current
    previous = [str(m.get("content") or "").strip() for m in history
                if m.get("role") == "user" and m.get("content")]
    previous = [text for text in previous if text != question.strip()][-2:]
    if not previous:
        return current
    return "\n".join(text[:350] for text in previous) + "\n追问：" + current


def build_code_query(code: str, question: str | None, clues: dict) -> str:
    """保留问题、结构与静态线索，避免大段代码淹没检索问题。"""
    terms: list[str] = []
    patterns = (
        (r"->\s*(next|prev)\b|\blinked.?list\b", "链表 指针顺序 插入 删除"),
        (r"->\s*(left|right)\b|\b(BST|AVL)\b", "二叉树 二叉排序树"),
        (r"\b(leftRotate|rightRotate|rotate|rotation)\b", "AVL 树旋转 平衡因子"),
        (r"\b(malloc|calloc|new|delete|free)\b", "内存释放 悬空指针 内存泄漏"),
        (r"\b(stack|push|pop)\b", "栈 栈顶 边界"),
        (r"\b(queue|enqueue|dequeue)\b", "队列 判空 判满"),
    )
    for pattern, label in patterns:
        if re.search(pattern, code, flags=re.IGNORECASE):
            terms.append(label)
    if clues.get("可能的递归"):
        terms.append("递归 终止条件 基线")
    lines = [str(question or "").strip()[:600], " ".join(terms)]
    for kind, entries in clues.items():
        lines.append(kind + "：" + "; ".join(str(entry)[:150] for entry in entries[:2]))
    # 无静态线索也保留一个短窗口供向量检索识别算法。
    lines.append(code[:500])
    return "\n".join(line for line in lines if line)[:1800]


def _bounded_history(history: list[dict], budget: int = HISTORY_TOKEN_BUDGET) -> list[dict]:
    selected: list[dict] = []
    used = 0
    for msg in reversed(history):
        if msg.get("role") not in ("user", "assistant") or not msg.get("content"):
            continue
        content = str(msg["content"])
        cost = estimate_tokens(content) + 8
        if used + cost > budget:
            # 不拆代码或句子，也不越过大消息拼接更早的失去上下文的历史。
            break
        selected.append({"role": msg["role"], "content": content})
        used += cost
    return list(reversed(selected))


def _build_chat_messages(question: str, history: list[dict], retrieved: list[dict]) -> list[dict]:
    messages = [{"role": "system", "content": SOCRATIC_SYSTEM + "\n\n" + build_context(retrieved)}]
    messages.extend(_bounded_history(history))
    messages.append({"role": "user", "content": question})
    return messages


def _references(retrieved: list[dict]) -> list[dict]:
    references: list[dict] = []
    seen: set[str] = set()
    for item in retrieved:
        identity = item.get("chunk_id") or f"{item.get('category')}:{item.get('source')}:{item.get('section')}"
        if identity in seen:
            continue
        seen.add(identity)
        references.append({key: item.get(key) for key in (
            "kp_id", "title", "chapter", "category", "source", "section", "chunk_id",
            "document_id", "index_version", "retrieval",
        )})
    return references


def answer_stream(question: str, history: list[dict] | None = None, api_key: str | None = None):
    """先输出实际进入上下文的片段引用，再流式输出教学回答。"""
    history = history or []
    query = build_retrieval_query(question, history)
    retrieved = select_context(rag.search(query, audience="hint"))
    messages = _build_chat_messages(question, history, retrieved)
    yield ("references", _references(retrieved))
    for token in chat_stream(messages, api_key=api_key):
        yield ("token", token)



def _select_code_context(results: list[dict]) -> list[dict]:
    """预算先为两个知识点片段、一个 Bug 片段留位，其余保留原排名。"""
    safe = [item for item in results
            if item.get("audience", "hint") == "hint" and item.get("category") != "solutions"]
    reserved = ([index for index, item in enumerate(safe) if item.get("category") == "kp"][:2]
                + [index for index, item in enumerate(safe) if item.get("category") == "buglib"][:1])
    priority = set(reserved)
    ordered = [safe[index] for index in reserved]
    ordered.extend(item for index, item in enumerate(safe) if index not in priority)
    return select_context(ordered)


def analyze_code_stream(
    code: str,
    language: str = "cpp",
    question: str | None = None,
    api_key: str | None = None,
):
    """代码静态线索只提取一次，单次检索保留知识点与 Bug 案例配额。"""
    clues = code_parser.analyze(code)
    query = build_code_query(code, question, clues)
    retrieved = _select_code_context(rag.search(
        query,
        categories=[rag.KP_COLLECTION, "buglib", "lecture"],
        top_k=6,
        audience="hint",
        quotas={"kp": 2, "buglib": 1},
    ))
    kp_ids = list(dict.fromkeys(item["kp_id"] for item in retrieved if item.get("kp_id")))
    system = CODE_DIAGNOSIS_SYSTEM + "\n\n" + build_context(retrieved)
    system += "\n\n" + build_diagnosis_protocol(kp_ids)
    user_content = f"学生提交的代码（{language}）：\n```{language}\n{code}\n```\n"
    if clues:
        lines = ["\n代码静态分析线索（可能有误，仅供参考定位，不要照搬，不要给完整修复代码）："]
        for kind, entries in clues.items():
            lines.append(f"- {kind}：{'; '.join(str(entry)[:200] for entry in entries[:8])}")
        user_content += "\n".join(lines) + "\n"
    if question:
        user_content += f"\n学生的问题：{question}\n"
    user_content += "\n请先诊断问题，再以提问引导学生自己修复，不要给出完整代码。"
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_content}]
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
    # 模型返回的统计标签也必须有本次课程证据，不能凭空写入掌握度。
    parsed["kp_ids"] = [kp for kp in parsed.get("kp_ids", []) if kp in kp_ids]
    yield ("diagnosis", parsed)
