"""RAG 知识库：文档分块、ChromaDB 建库与检索。"""
from __future__ import annotations

import os
import re
from pathlib import Path

# 禁用 chromadb 遥测，避免与部分依赖版本不兼容导致的无害报错刷屏
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb

from app.config import KNOWLEDGE_DIR, VECTOR_DB_DIR, TOP_K
from app.core.embedding import embed_texts

# 三类知识库：讲义 / 题解 / 高频 bug 库
COLLECTIONS = ["lecture", "solutions", "buglib"]

_client: chromadb.PersistentClient | None = None


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


def ingest() -> dict:
    """建库（幂等：以稳定的 doc_id upsert，重复执行不产生重复数据）。"""
    db = get_db()
    stats = {}
    for cname in COLLECTIONS:
        coll = db.get_or_create_collection(name=cname)
        src_dir = KNOWLEDGE_DIR / cname
        docs, ids, metas = [], [], []
        if src_dir.exists():
            for md_file in sorted(src_dir.glob("*.md")):
                text = md_file.read_text(encoding="utf-8")
                for idx, chunk in enumerate(split_markdown(text)):
                    ids.append(f"{cname}:{md_file.stem}:{idx}")
                    docs.append(chunk)
                    metas.append({"source": md_file.name, "category": cname})
        if docs:
            embeddings = embed_texts(docs)
            coll.upsert(documents=docs, embeddings=embeddings, ids=ids, metadatas=metas)
        stats[cname] = coll.count()
    return stats


def search(query: str, categories: list[str] | None = None, top_k: int = TOP_K) -> list[dict]:
    """检索 top_k 相关知识片段，返回按相关度排序的结果。"""
    db = get_db()
    cats = categories or COLLECTIONS
    q_emb = embed_texts([query])[0]
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
                "category": cname,
                "source": meta.get("source", ""),
                "text": doc,
                "distance": res["distances"][0][i],
            })
    results.sort(key=lambda x: x["distance"])
    return results[:top_k]


def stats() -> dict:
    db = get_db()
    return {cname: db.get_or_create_collection(name=cname).count() for cname in COLLECTIONS}
