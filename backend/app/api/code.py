"""代码剖析接口（SSE 流式 + 结构化诊断 + 作业提交）。"""
import json

from fastapi import APIRouter, Depends, Header, HTTPException
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
    assignment_id: int | None = None


def _sse(payload) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream(
    code: str,
    language: str,
    question: str | None,
    user_id: int,
    analysis_id: int,
    assignment_id: int | None,
    api_key: str | None,
):
    try:
        full = ""
        diagnosis = {}
        for kind, payload in analyze_code_stream(code, language, question, api_key=api_key):
            if kind == "token":
                full += payload
                yield _sse({"token": payload})
            elif kind == "diagnosis":
                diagnosis = payload
                yield _sse({"diagnosis": payload})

        # 剖析完成，写入数据库（含结构化诊断）
        store.update_code_analysis_result(analysis_id, user_id, full, code, question, diagnosis)

        if assignment_id:
            submission_id = store.upsert_submission(
                assignment_id=assignment_id,
                user_id=user_id,
                content=code,
                language=language,
                status="analyzed",
                ai_result=full,
                diagnosis=diagnosis,
            )
            # 按诊断到的知识点累计掌握度（教师端/学生端首页用）
            store.record_mastery(
                user_id,
                diagnosis.get("kp_ids"),
                diagnosis.get("hint_level_reached"),
                diagnosis.get("severity"),
            )
            yield _sse({"submission_id": submission_id})

        yield _sse({"analysis_id": analysis_id, "done": True})
    except Exception as e:
        yield _sse({"error": str(e)})
        yield _sse({"done": True})


@router.post("/code/analyze")
def analyze_endpoint(
    req: CodeRequest,
    user: dict = Depends(get_current_user),
    x_llm_key: str | None = Header(None, alias="X-LLM-Key"),
):
    if req.assignment_id is not None:
        assignment = store.get_assignment(req.assignment_id)
        if not assignment:
            raise HTTPException(404, "任务不存在")
        if not store.is_member(assignment["class_id"], user["user_id"]):
            raise HTTPException(403, "你不在该任务所属的班级里")
        if assignment["type"] != "code":
            raise HTTPException(400, "该任务不是代码类任务")
        if store.assignment_closed(assignment):
            raise HTTPException(400, "任务已截止，不接受提交")

    # 先建一条空记录，用于承接流式结果
    rec = store.create_code_analysis(user["user_id"], req.code, req.language, req.question)
    return StreamingResponse(
        _stream(
            req.code,
            req.language,
            req.question,
            user["user_id"],
            rec["id"],
            req.assignment_id,
            x_llm_key,
        ),
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
