"""知识库建库与统计接口。"""
from fastapi import APIRouter

from app.core import rag

router = APIRouter(prefix="/api", tags=["knowledge"])


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
