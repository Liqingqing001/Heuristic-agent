"""代码剖析接口（SSE 流式 + 后端持久化）。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.socratic import analyze_code_stream
from app.core import store
from app.core.auth import get_current_user

router = APIRouter(prefix="/api", tags=["code"])


class CodeRequest(BaseModel):
    code: str
    language: str = "cpp"
    question: str | None = None


def _sse(payload) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream(code: str, language: str, question: str | None, user_id: int, analysis_id: int):
    try:
        full = ""
        for token in analyze_code_stream(code, language, question):
            full += token
            yield _sse({"token": token})
        # 剖析完成，写入数据库
        store.update_code_analysis_result(analysis_id, user_id, full, code, question)
        yield _sse({"analysis_id": analysis_id, "done": True})
    except Exception as e:
        yield _sse({"error": str(e)})
        yield _sse({"done": True})


@router.post("/code/analyze")
def analyze_endpoint(req: CodeRequest, user: dict = Depends(get_current_user)):
    # 先建一条空记录，用于承接流式结果
    rec = store.create_code_analysis(user["user_id"], req.code, req.language, req.question)
    return StreamingResponse(
        _stream(req.code, req.language, req.question, user["user_id"], rec["id"]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/code/analyses")
def list_analyses(user: dict = Depends(get_current_user)):
    return store.list_code_analyses(user["user_id"])


@router.get("/code/analyses/{analysis_id}")
def get_analysis(analysis_id: int, user: dict = Depends(get_current_user)):
    rec = store.get_code_analysis(analysis_id, user["user_id"])
    if not rec:
        raise HTTPException(404, "记录不存在或无权访问")
    return rec


@router.delete("/code/analyses/{analysis_id}")
def delete_analysis(analysis_id: int, user: dict = Depends(get_current_user)):
    store.delete_code_analysis(analysis_id, user["user_id"])
    return {"status": "ok"}