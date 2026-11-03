"""不依赖模型的中文 BM25 召回、排名融合与文档多样性选择。

lexical_score 与向量距离不在同一量纲，只通过 RRF 排名融合。
relevance 是词面证据覆盖度，不能当作经过校准的相关性概率。
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

# 只在连续中文串内部取二字组，不把标点两侧的字拼成不存在的词。
_CHINESE = re.compile(r"[\u4e00-\u9fff]+")
_IDENTIFIERS = re.compile(r"[a-z_][a-z0-9_]*|[0-9]+", re.I)
_MEMBERS = re.compile(r"[a-z_]\w*(?:\s*(?:->|\.)\s*[a-z_]\w*)+", re.I)
_STOP_GRAMS = frozenset({"如何", "怎么", "什么", "为何", "是否", "可以", "一个", "一下", "帮我", "请问", "进行", "学生"})
_ALIAS_GROUPS = (
    ("二叉搜索树", "二叉排序树", "bst"),
    ("深度优先", "dfs"),
    ("广度优先", "宽度优先", "bfs"),
    ("快慢指针", "双指针"),
    ("哈希表", "散列表", "hash"),
    ("迪杰斯特拉", "dijkstra"),
    ("快速排序", "快排", "quicksort"),
    ("归并排序", "mergesort"),
    ("链表", "linkedlist"),
    ("队列", "queue"),
    ("堆栈", "栈", "stack"),
)


def tokenize(text: str) -> list[str]:
    """中文二字组与代码标识符；成员访问另保留完整符号串。"""
    text = (text or "").lower()
    terms: list[str] = []
    for run in _CHINESE.findall(text):
        if len(run) == 1:
            terms.append("zh:" + run)
        else:
            terms.extend("zh:" + run[i:i + 2] for i in range(len(run) - 1) if run[i:i + 2] not in _STOP_GRAMS)
    terms.extend("id:" + word for word in _IDENTIFIERS.findall(text))
    terms.extend("code:" + re.sub(r"\s+", "", member) for member in _MEMBERS.findall(text))
    return terms


def expand_query(query: str) -> str:
    """只扩展明确出现的同义词，避免引入额外模型请求。"""
    lower = query.lower()
    additions: list[str] = []
    for group in _ALIAS_GROUPS:
        if any((re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", lower) if alias.isascii() else alias in lower) for alias in group):
            additions.extend(group)
    return query + (" " + " ".join(additions) if additions else "")


@dataclass(frozen=True)
class _Index:
    fields: tuple[tuple[Counter, Counter, Counter], ...]
    lengths: tuple[tuple[int, int, int], ...]
    averages: tuple[float, float, float]
    frequencies: Counter


@lru_cache(maxsize=8)
def _prepare(rows: tuple[tuple[str, str, str, str, str], ...]) -> _Index:
    fields, lengths = [], []
    frequencies = Counter()
    for _, _, title, section, text in rows:
        counts = tuple(Counter(tokenize(value)) for value in (title, section, text))
        fields.append(counts)
        lengths.append(tuple(sum(counter.values()) for counter in counts))
        frequencies.update(set().union(*(set(counter) for counter in counts)))
    averages = tuple(sum(row[i] for row in lengths) / max(len(rows), 1) for i in range(3))
    return _Index(tuple(fields), tuple(lengths), averages, frequencies)


def _rows(chunks: list[dict]) -> tuple[tuple[str, str, str, str, str], ...]:
    return tuple((
        str(chunk["chunk_id"]),
        str(chunk.get("content_hash") or hashlib.sha256(chunk["text"].encode()).hexdigest()),
        str(chunk.get("title") or ""),
        str(chunk.get("section") or ""),
        chunk["text"],
    ) for chunk in chunks)


def lexical_rank(query: str, chunks: Iterable[dict], limit: int = 20) -> list[dict]:
    """BM25 分字段召回。弱词面重叠不产生结果，不填充无关片段。

    有效证据：至少两个不同二字组，或精确 ASCII 标识符/成员表达式，
    或短中文查询完整命中标题、小节或正文。返回值保留调用方的元数据。
    """
    if limit <= 0 or not query.strip():
        return []
    chunks = list(chunks)
    if not chunks:
        return []
    query_terms = set(tokenize(expand_query(query)))
    if not query_terms:
        return []
    index = _prepare(_rows(chunks))
    short_chinese = query.strip() if re.fullmatch(r"[\u4e00-\u9fff]{1,4}", query.strip()) else ""
    ranked = []
    n = len(chunks)
    for position, chunk in enumerate(chunks):
        fields = index.fields[position]
        matches = query_terms & set().union(*(set(counter) for counter in fields))
        chinese_matches = {term for term in matches if term.startswith("zh:") and len(term[3:]) >= 2}
        exact_identifiers = {term for term in matches if term.startswith("code:") or (term.startswith("id:") and len(term[3:]) >= 2)}
        phrase_match = bool(short_chinese and any(short_chinese in str(chunk.get(field) or "") for field in ("title", "section", "text")))
        if len(chinese_matches) < 2 and not exact_identifiers and not phrase_match:
            continue
        # 单字概念（如“栈”“堆”）无法靠二字组命中，保留精确短语证据。
        score = 0.5 * sum(boost for field, boost in (("title", 3.0), ("section", 2.0), ("text", 1.0)) if short_chinese and short_chinese in str(chunk.get(field) or ""))
        for field_number, boost in enumerate((3.0, 2.0, 1.0)):
            counts = fields[field_number]
            length = index.lengths[position][field_number]
            average = max(index.averages[field_number], 1)
            for term in matches:
                frequency = counts[term]
                if not frequency:
                    continue
                df = index.frequencies[term]
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                score += boost * idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length / average))
        if score > 0:
            relevance = len(matches) / len(query_terms)
            ranked.append({**chunk, "lexical_score": score, "relevance": min(1.0, max(relevance, 0.5 if phrase_match or exact_identifiers else 0.0)), "retrieval": "lexical"})
    ranked.sort(key=lambda chunk: (-chunk["lexical_score"], str(chunk["chunk_id"])))
    return ranked[:limit]


def rrf(rankings: list[list[dict]], limit: int = 20) -> list[dict]:
    """Reciprocal Rank Fusion（k=60）；同一列表中的重复片段只计一次。"""
    if limit <= 0:
        return []
    results: dict[str, dict] = {}
    scores = Counter()
    sources = Counter()
    nonempty = sum(bool(ranking) for ranking in rankings)
    for ranking in rankings:
        seen = set()
        for rank, chunk in enumerate(ranking, 1):
            chunk_id = chunk["chunk_id"]
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            scores[chunk_id] += 1.0 / (60 + rank)
            sources[chunk_id] += 1
            if chunk_id not in results:
                results[chunk_id] = dict(chunk)
            else:
                for key, value in chunk.items():
                    results[chunk_id].setdefault(key, value)
                for key in ("lexical_score", "relevance"):
                    if key in chunk:
                        results[chunk_id][key] = max(results[chunk_id].get(key, 0), chunk[key])
    ordered = sorted(results, key=lambda key: (-scores[key], str(key)))
    theoretical_max = max(nonempty, 1) / 61
    return [{**results[key], "rrf_score": scores[key], "distance": max(0.0, 1.0 - scores[key] / theoretical_max), "retrieval": "hybrid" if sources[key] > 1 else results[key].get("retrieval", "vector")} for key in ordered[:limit]]


def select_diverse(results: list[dict], top_k: int, per_document: int = 2, quotas: dict | None = None) -> list[dict]:
    """先按配额保留类别，再按原排名补齐；最终维持原始相对顺序。

    配额总数超过 top_k 时按 quotas 的插入顺序分配；配额不会打破文档上限。
    """
    if top_k <= 0 or per_document <= 0:
        return []
    chosen: set[str] = set()
    counts = Counter()

    def add(chunk: dict) -> bool:
        document_id = chunk.get("document_id") or chunk.get("source") or chunk["chunk_id"]
        if len(chosen) >= top_k or chunk["chunk_id"] in chosen or counts[document_id] >= per_document:
            return False
        chosen.add(chunk["chunk_id"])
        counts[document_id] += 1
        return True

    for category, count in (quotas or {}).items():
        reserved = 0
        for chunk in results:
            if reserved >= max(0, count):
                break
            if chunk.get("category") == category and add(chunk):
                reserved += 1
    for chunk in results:
        add(chunk)
    emitted = set()
    selected = []
    for chunk in results:
        if chunk["chunk_id"] in chosen and chunk["chunk_id"] not in emitted:
            selected.append(chunk)
            emitted.add(chunk["chunk_id"])
    return selected
