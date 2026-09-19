"""知识库建库、统计、浏览、搜索接口。"""
from pathlib import Path
from fastapi import APIRouter, Query
import re

from app.core import rag

router = APIRouter(prefix="/api", tags=["knowledge"])

# 知识库根目录：backend/data/knowledge/
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge"

CATEGORIES = {
    "lecture": "讲义",
    "solutions": "题解",
    "buglib": "Bug库",
}


def _parse_md(path: Path):
    """解析一个 Markdown 文件，按二级标题 ## 分块"""
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


@router.post("/knowledge/ingest")
def ingest():
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
def list_knowledge(category: str = Query("lecture")):
    """列出某个分类下的所有知识条目"""
    folder = KNOWLEDGE_DIR / category
    if not folder.exists():
        return {"items": [], "total": 0}

    items = []
    for md_file in sorted(folder.glob("*.md")):
        items.extend(_parse_md(md_file))

    return {"items": items, "total": len(items)}


@router.get("/knowledge/search")
def search_knowledge(q: str = Query(...), top_k: int = Query(20)):
    """简易搜索：遍历所有 Markdown，标题或内容包含关键词就返回"""
    q = q.strip()
    if not q:
        return {"items": [], "total": 0}

    q_lower = q.lower()
    items = []

    for cat_key in CATEGORIES:
        folder = KNOWLEDGE_DIR / cat_key
        if not folder.exists():
            continue
        for md_file in sorted(folder.glob("*.md")):
            for item in _parse_md(md_file):
                text = (item["title"] + " " + item["content"]).lower()
                if q_lower in text:
                    items.append({
                        **item,
                        "category": cat_key,
                        "category_name": CATEGORIES[cat_key],
                    })
                    if len(items) >= top_k:
                        break
            if len(items) >= top_k:
                break
        if len(items) >= top_k:
            break

    return {"items": items, "total": len(items)}