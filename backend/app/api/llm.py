"""模型状态接口：给前端状态横幅用（不返回任何密钥内容）。"""
from fastapi import APIRouter

from app.core import llm, rag

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/status")
def status():
    info = llm.status()
    try:
        info["knowledge"] = rag.stats()
    except Exception as exc:  # 向量库不可用时不影响登录和对话
        info["knowledge"] = {}
        info["knowledge_error"] = str(exc)
    info["retrieval"] = rag.retrieval_status()
    return info
