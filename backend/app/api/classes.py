"""班级、任务、提交与学情看板接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core import store
from app.core.auth import get_current_user

router = APIRouter(prefix="/api", tags=["classes"])


class CreateClassBody(BaseModel):
    name: str
    term: str = ""


class JoinClassBody(BaseModel):
    code: str


class CreateAssignmentBody(BaseModel):
    title: str
    description: str = ""
    type: str = "code"
    kp_ids: list[str] = []
    due_at: str | None = None


class SubmitTextBody(BaseModel):
    content: str


class GradeBody(BaseModel):
    score: float
    feedback: str = ""
    returned: bool = False


def _get_class_or_404(class_id: int) -> dict:
    cls = store.get_class(class_id)
    if not cls:
        raise HTTPException(404, "班级不存在")
    return cls


def _ensure_can_view(cls: dict, user: dict) -> None:
    if user["role"] == "teacher" and cls["teacher_id"] == user["user_id"]:
        return
    if store.is_member(cls["id"], user["user_id"]):
        return
    raise HTTPException(403, "无权访问该班级")


def _ensure_teacher_of(cls: dict, user: dict) -> None:
    if user["role"] != "teacher" or cls["teacher_id"] != user["user_id"]:
        raise HTTPException(403, "仅该班级的教师可操作")


@router.post("/classes")
def create_class(body: CreateClassBody, user: dict = Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(403, "只有教师账号可以创建班级")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "班级名称不能为空")
    return store.create_class(user["user_id"], name, body.term.strip())


@router.get("/classes")
def list_classes(user: dict = Depends(get_current_user)):
    """教师返回自己创建的班级，学生返回已加入的班级。"""
    if user["role"] == "teacher":
        return {"taught": store.list_classes_taught(user["user_id"]), "joined": []}
    return {"taught": [], "joined": store.list_classes_joined(user["user_id"])}


@router.post("/classes/join")
def join_class(body: JoinClassBody, user: dict = Depends(get_current_user)):
    code = body.code.strip()
    if not code:
        raise HTTPException(400, "请输入邀请码")
    result = store.join_class(code, user["user_id"])
    if result["status"] == "not_found":
        raise HTTPException(404, "邀请码不存在，请向老师确认")
    if result["status"] == "is_teacher":
        raise HTTPException(400, "你是该班级的教师，无需加入")
    return {"status": result["status"], "class": result.get("class")}


@router.get("/classes/{class_id}")
def get_class(class_id: int, user: dict = Depends(get_current_user)):
    cls = _get_class_or_404(class_id)
    _ensure_can_view(cls, user)
    return cls


@router.get("/classes/{class_id}/members")
def list_members(class_id: int, user: dict = Depends(get_current_user)):
    cls = _get_class_or_404(class_id)
    _ensure_can_view(cls, user)
    return store.list_members(class_id)


@router.get("/classes/{class_id}/assignments")
def list_assignments(class_id: int, user: dict = Depends(get_current_user)):
    cls = _get_class_or_404(class_id)
    _ensure_can_view(cls, user)
    return store.list_assignments(class_id, user["user_id"])


@router.post("/classes/{class_id}/assignments")
def create_assignment(
    class_id: int,
    body: CreateAssignmentBody,
    user: dict = Depends(get_current_user),
):
    cls = _get_class_or_404(class_id)
    _ensure_teacher_of(cls, user)
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "任务标题不能为空")
    if body.type not in ("code", "question"):
        raise HTTPException(400, "任务类型只能是 code 或 question")
    return store.create_assignment(
        class_id=class_id,
        title=title,
        description=body.description.strip(),
        type_=body.type,
        kp_ids=body.kp_ids,
        due_at=body.due_at,
        created_by=user["user_id"],
    )


@router.get("/classes/{class_id}/overview")
def class_overview(class_id: int, user: dict = Depends(get_current_user)):
    cls = _get_class_or_404(class_id)
    _ensure_teacher_of(cls, user)
    return store.class_overview(class_id)


@router.get("/assignments/{assignment_id}")
def get_assignment(assignment_id: int, user: dict = Depends(get_current_user)):
    assignment = store.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(404, "任务不存在")
    cls = _get_class_or_404(assignment["class_id"])
    _ensure_can_view(cls, user)
    return assignment


@router.get("/assignments/{assignment_id}/submissions")
def list_submissions(assignment_id: int, user: dict = Depends(get_current_user)):
    assignment = store.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(404, "任务不存在")
    cls = _get_class_or_404(assignment["class_id"])
    _ensure_teacher_of(cls, user)
    return store.list_submissions(assignment_id)


@router.post("/assignments/{assignment_id}/submit")
def submit_text(
    assignment_id: int,
    body: SubmitTextBody,
    user: dict = Depends(get_current_user),
):
    """文字类任务提交（代码类任务走 /api/code/analyze 并带上 assignment_id）。"""
    assignment = store.get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(404, "任务不存在")
    if not store.is_member(assignment["class_id"], user["user_id"]):
        raise HTTPException(403, "你不在该任务所属的班级里")
    if assignment["type"] != "question":
        raise HTTPException(400, "该任务是代码类任务，请到代码剖析页提交")
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "回答不能为空")
    submission_id = store.upsert_submission(
        assignment_id=assignment_id,
        user_id=user["user_id"],
        content=content,
        language="text",
        status="submitted",
        ai_result="",
        diagnosis={},
    )
    return {"submission_id": submission_id, "status": "submitted"}


@router.get("/submissions/{submission_id}")
def get_submission(submission_id: int, user: dict = Depends(get_current_user)):
    submission = store.get_submission(submission_id)
    if not submission:
        raise HTTPException(404, "提交记录不存在")
    assignment = store.get_assignment(submission["assignment_id"])
    cls = _get_class_or_404(assignment["class_id"]) if assignment else None
    if submission["user_id"] != user["user_id"]:
        if not cls:
            raise HTTPException(403, "无权访问")
        _ensure_teacher_of(cls, user)
    return submission


@router.patch("/submissions/{submission_id}/grade")
def grade_submission(
    submission_id: int,
    body: GradeBody,
    user: dict = Depends(get_current_user),
):
    submission = store.get_submission(submission_id)
    if not submission:
        raise HTTPException(404, "提交记录不存在")
    assignment = store.get_assignment(submission["assignment_id"])
    if not assignment:
        raise HTTPException(404, "任务不存在")
    cls = _get_class_or_404(assignment["class_id"])
    _ensure_teacher_of(cls, user)

    if not 0 <= body.score <= 100:
        raise HTTPException(400, "分数必须在 0-100 之间")
    if len(body.feedback) > 500:
        raise HTTPException(400, "评语最多 500 字")

    updated = store.grade_submission(
        submission_id,
        user["user_id"],
        body.score,
        body.feedback,
        body.returned,
    )
    if not updated:
        raise HTTPException(400, "批阅失败")
    return updated


@router.get("/classes/{class_id}/mastery")
def class_mastery(class_id: int, user: dict = Depends(get_current_user)):
    cls = _get_class_or_404(class_id)
    _ensure_teacher_of(cls, user)
    return {"items": store.class_mastery(class_id)}


@router.get("/mastery/me")
def my_mastery(user: dict = Depends(get_current_user)):
    return {"items": store.mastery_for_user(user["user_id"])}
