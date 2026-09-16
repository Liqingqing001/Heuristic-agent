"""代码剖析接口（SSE 流式，苏格拉底式诊断引导）。"""
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.socratic import analyze_code_stream

router = APIRouter(prefix="/api", tags=["code"])


class CodeRequest(BaseModel):
    code: str
    language: str = "cpp"
    question: str | None = None


def _sse(payload) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream(code: str, language: str, question: str | None):
    try:
        for token in analyze_code_stream(code, language, question):
            yield _sse({"token": token})
        yield _sse({"done": True})
    except Exception as e:
        yield _sse({"error": str(e)})
        yield _sse({"done": True})


@router.post("/code/analyze")
def analyze_endpoint(req: CodeRequest):
    return StreamingResponse(
        _stream(req.code, req.language, req.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
