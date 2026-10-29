"""RAG 知识库：文档分块、ChromaDB 建库与检索。

四类知识库：
- ``lecture``   讲义
- ``solutions`` 题解
- ``buglib``    高频 bug 库
- ``kp``        结构化知识点（带 kp_id / 章节 / 难度 / 前置元数据）
"""
from __future__ import annotations

import os
import re

# 禁用 chromadb 遥测，避免与部分依赖版本不兼容导致的无害报错刷屏
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# 兼容垫片：chromadb 0.4.x 内部仍在引用 numpy 2.0 已删除的别名 np.float_，
# 在 numpy>=2 的环境下不加这行会直接 ImportError。升级到 chromadb>=1.0 后可删。
import numpy as _np

if not hasattr(_np, "float_"):
    _np.float_ = _np.float64

import chromadb

from app.config import KNOWLEDGE_DIR, TOP_K, VECTOR_DB_DIR
from app.core.embedding import embed_texts
from app.utils import kp_meta

#: 知识点 collection 名（chromadb 要求 3-63 个字符）
KP_COLLECTION = "kp_points"

# 四类知识库：讲义 / 题解 / 高频 bug 库 / 结构化知识点
COLLECTIONS = ["lecture", "solutions", "buglib", KP_COLLECTION]

_client: chromadb.PersistentClient | None = None

#: 向量模型加载失败后置为 True，之后直接走关键词降级，避免每次请求都重试
_embedding_broken = False


def get_db() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    return _client


def split_markdown(text: str) -> list[str]:
    """按二级标题(## )切分；无标题文档按空行分块。"""
    parts = re.split(r"\n(?=## )", text)
    chunks = []
    for p in parts:
        p = p.strip()
        if p:
            chunks.append(p)
    return chunks


def _ingest_plain(coll, src_dir) -> int:
    """讲义 / 题解 / bug 库：按二级标题分块。"""
    docs, ids, metas = [], [], []
    if src_dir.exists():
        for md_file in sorted(src_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            for idx, chunk in enumerate(split_markdown(text)):
                ids.append(f"{src_dir.name}:{md_file.stem}:{idx}")
                docs.append(chunk)
                metas.append({"source": md_file.name, "category": src_dir.name})
    if docs:
        embeddings = embed_texts(docs)
        coll.upsert(documents=docs, embeddings=embeddings, ids=ids, metadatas=metas)
    return coll.count()


def _ingest_kp(coll) -> int:
    """结构化知识点：按 ## 小节分块，元数据带 kp_id / 章节 / 难度 / 前置。"""
    src_dir = KNOWLEDGE_DIR / "kp"
    docs, ids, metas = [], [], []
    for path in kp_meta.iter_kp_files(src_dir):
        kp = kp_meta.load_kp(path)
        base = kp_meta.to_vector_metadata(kp)
        if not base.get("kp_id"):
            continue
        for idx, (heading, body) in enumerate(kp["sections"].items()):
            body = body.strip()
            if not body:
                continue
            # 把知识点标题和小节标题拼进正文，提升检索命中率
            doc = f"{base['title']}｜{heading}\n{body}"
            ids.append(f"kp:{base['kp_id']}:{idx}:{heading}")
            docs.append(doc)
            metas.append({
                **base,
                "category": "kp",
                "section": heading,
                "origin": base.get("source", ""),
                "source": path.name,
            })
    if docs:
        embeddings = embed_texts(docs)
        coll.upsert(documents=docs, embeddings=embeddings, ids=ids, metadatas=metas)
    return coll.count()


def ingest() -> dict:
    """建库（幂等：以稳定的 doc_id upsert，重复执行不产生重复数据）。"""
    db = get_db()
    stats = {}
    for cname in COLLECTIONS:
        coll = db.get_or_create_collection(name=cname)
        if cname == KP_COLLECTION:
            stats[cname] = _ingest_kp(coll)
        else:
            stats[cname] = _ingest_plain(coll, KNOWLEDGE_DIR / cname)
    return stats


def search(query: str, categories: list[str] | None = None, top_k: int = TOP_K) -> list[dict]:
    """检索 top_k 相关知识片段，返回按相关度排序的结果。

    向量模型不可用（例如 torch 被系统策略拦截）时自动降级为关键词检索，
    保证「检索带 kp_id」这条链路在任何机器上都能跑通。
    """
    global _embedding_broken
    cats = categories or COLLECTIONS
    if _embedding_broken:
        return _lexical_search(query, cats, top_k)

    db = get_db()
    try:
        q_emb = embed_texts([query])[0]
    except Exception as e:
        _embedding_broken = True
        print(f"[rag] 向量模型不可用，检索降级为关键词匹配：{e}")
        return _lexical_search(query, cats, top_k)

    results: list[dict] = []
    for cname in cats:
        try:
            coll = db.get_or_create_collection(name=cname)
        except Exception:
            continue
        if coll.count() == 0:
            continue
        res = coll.query(query_embeddings=[q_emb], n_results=top_k)
        for i, doc in enumerate(res["documents"][0]):
            meta = res["metadatas"][0][i] or {}
            results.append({
                "category": "kp" if cname == KP_COLLECTION else cname,
                "source": meta.get("source", ""),
                "text": doc,
                "distance": res["distances"][0][i],
                "kp_id": meta.get("kp_id"),
                "title": meta.get("title"),
                "chapter": meta.get("chapter"),
                "difficulty": meta.get("difficulty"),
                "section": meta.get("section"),
            })
    results.sort(key=lambda x: x["distance"])
    return results[:top_k]


# ---------------------------------------------------------------- 关键词降级

def _bigrams(text: str) -> set[str]:
    """中文按二字组切分，英文/数字按词切分，用于粗糙的相似度打分。"""
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "", text.lower())
    grams = {cleaned[i:i + 2] for i in range(len(cleaned) - 1)}
    for word in re.findall(r"[a-z0-9_]{2,}", text.lower()):
        grams.add(word)
    return grams


def _local_chunks() -> list[dict]:
    """不依赖向量库，直接从磁盘重建检索块（数据量小，实时构建即可）。"""
    chunks: list[dict] = []
    for cname in ("lecture", "solutions", "buglib"):
        folder = KNOWLEDGE_DIR / cname
        if not folder.exists():
            continue
        for md_file in sorted(folder.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            for chunk in split_markdown(text):
                chunks.append({
                    "category": cname,
                    "source": md_file.name,
                    "text": chunk,
                    "kp_id": None,
                    "title": None,
                    "chapter": None,
                    "difficulty": None,
                    "section": None,
                })
    for path in kp_meta.iter_kp_files(KNOWLEDGE_DIR / "kp"):
        try:
            kp = kp_meta.load_kp(path)
        except Exception:
            continue
        base = kp_meta.to_vector_metadata(kp)
        for heading, body in kp["sections"].items():
            body = body.strip()
            if not body:
                continue
            chunks.append({
                "category": "kp",
                "source": path.name,
                "text": f"{base['title']}｜{heading}\n{body}",
                "kp_id": base["kp_id"],
                "title": base["title"],
                "chapter": base["chapter"],
                "difficulty": base["difficulty"],
                "section": heading,
            })
    return chunks


def _lexical_search(query: str, cats: list[str], top_k: int) -> list[dict]:
    grams = _bigrams(query)
    if not grams:
        return []
    scored: list[dict] = []
    for chunk in _local_chunks():
        if chunk["category"] not in cats and not (
            chunk["category"] == "kp" and KP_COLLECTION in cats
        ):
            continue
        title = chunk.get("title") or ""
        # 标题重复三次做加权，让"知识点标题命中"优先于正文里偶然出现的词
        doc_grams = _bigrams(chunk["text"] + (" " + title) * 3)
        overlap = len(grams & doc_grams)
        if not overlap:
            continue
        score = overlap / (len(grams) ** 0.5 * (len(doc_grams) ** 0.3 + 1))
        if chunk["kp_id"] and chunk["title"] and query.strip() in chunk["title"]:
            score += 0.5
        scored.append({**chunk, "distance": round(1 - score, 6), "retrieval": "lexical"})
    scored.sort(key=lambda item: item["distance"])
    return scored[:top_k]


def stats() -> dict:
    db = get_db()
    return {cname: db.get_or_create_collection(name=cname).count() for cname in COLLECTIONS}
