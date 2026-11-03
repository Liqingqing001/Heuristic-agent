"""知识库建库、统计、浏览、搜索接口。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core import rag
from app.core.auth import require_teacher
from app.utils import kp_meta

router = APIRouter(prefix="/api", tags=["knowledge"])

# 知识库根目录：backend/data/knowledge/
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge"

CATEGORIES = {
    "lecture": "讲义",
    "solutions": "题解",
    "buglib": "Bug库",
    "kp": "知识点",
}


def _parse_md(path: Path):
    """解析一个 Markdown 文件，按二级标题 ## 分块。"""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    parts = re.split(r"^##\s+", text, flags=re.MULTILINE)
    items = []
    for part in parts[1:]:
        lines = part.split("\n", 1)
        title = lines[0].strip()
        content = lines[1].strip() if len(lines) > 1 else ""
        if title:
            items.append({
                "title": title,
                "content": content,
                "source": path.stem,
            })
    return items


def _parse_kp(path: Path) -> list[dict]:
    """知识点文件：一个文件算一条，标题取自 front matter。"""
    try:
        kp = kp_meta.load_kp(path)
    except Exception:
        return []
    meta = kp["meta"]
    sections = kp["sections"]
    content = "\n\n".join(
        f"## {name}\n{text}" for name, text in sections.items() if text
    )
    return [{
        "title": str(meta.get("title") or path.stem),
        "content": content,
        "source": path.stem,
        "kp_id": meta.get("id"),
        "chapter": meta.get("chapter"),
        "difficulty": meta.get("difficulty"),
        "type": meta.get("type"),
    }]


def _items_of(category: str) -> list[dict]:
    folder = KNOWLEDGE_DIR / category
    if not folder.exists():
        return []
    items: list[dict] = []
    for md_file in sorted(folder.glob("*.md")):
        if md_file.name.startswith("_") or md_file.name.lower() == "readme.md":
            continue
        if category == "kp":
            items.extend(_parse_kp(md_file))
        else:
            items.extend(_parse_md(md_file))
    return items


@router.post("/knowledge/ingest")
def ingest(_: dict = Depends(require_teacher)):
    """触发建库（幂等）。首次会下载 BGE 模型，耗时较长。"""
    try:
        stats = rag.ingest()
        return {"status": "ok", "stats": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/knowledge/stats")
def stats():
    """返回各类知识库的文档（分块）数量。"""
    return rag.stats()


@router.get("/knowledge/list")
def list_knowledge(category: Literal["lecture", "solutions", "buglib", "kp"] = Query("lecture")):
    """列出某个分类下的所有知识条目。"""
    items = _items_of(category)
    return {"items": items, "total": len(items)}


@router.get("/knowledge/search")
def search_knowledge(q: str = Query(...), top_k: int = Query(20, ge=1, le=100)):
    """简易搜索：遍历所有 Markdown，标题或内容包含关键词就返回。"""
    q = q.strip()
    if not q:
        return {"items": [], "total": 0}

    q_lower = q.lower()
    items = []

    for cat_key in CATEGORIES:
        if len(items) >= top_k:
            break
        for item in _items_of(cat_key):
            text = (item["title"] + " " + item["content"]).lower()
            if q_lower in text:
                items.append({
                    **item,
                    "category": cat_key,
                    "category_name": CATEGORIES[cat_key],
                })
                if len(items) >= top_k:
                    break

    return {"items": items, "total": len(items)}


@router.get("/knowledge/retrieval/status")
def retrieval_status():
    """检索模式、索引新旧与向量后端状态（不返回查询或模型密钥）。"""
    return rag.retrieval_status()


@router.post("/knowledge/retrieval/reset")
def reset_retrieval(_: dict = Depends(require_teacher)):
    """解除模型失败冷却；下一次检索重试向量，旧索引保持不变。"""
    return rag.reset_retrieval()
