"""个人资料与账号安全接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core import store
from app.core.auth import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/profile", tags=["profile"])

_MAX_LENGTH = {
    "display_name": 30,
    "real_name": 30,
    "school": 60,
    "department": 60,
    "major": 60,
    "gender": 10,
    "enrollment_year": 10,
    "bio": 300,
}


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    real_name: str | None = None
    school: str | None = None
    department: str | None = None
    major: str | None = None
    gender: str | None = None
    enrollment_year: str | None = None
    bio: str | None = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


@router.get("")
def get_profile(user: dict = Depends(get_current_user)):
    profile = store.get_profile(user["user_id"])
    if not profile:
        raise HTTPException(404, "用户不存在")
    return profile


@router.patch("")
def update_profile(body: ProfileUpdate, user: dict = Depends(get_current_user)):
    data = body.model_dump(exclude_unset=True)
    cleaned: dict[str, str] = {}
    for key, value in data.items():
        text = (value or "").strip()
        limit = _MAX_LENGTH.get(key, 60)
        if len(text) > limit:
            raise HTTPException(400, f"{key} 最多 {limit} 个字符")
        cleaned[key] = text

    if "display_name" in cleaned and not cleaned["display_name"]:
        raise HTTPException(400, "昵称不能为空")

    profile = store.update_profile(user["user_id"], cleaned)
    return profile


@router.post("/password")
def change_password(body: PasswordChange, user: dict = Depends(get_current_user)):
    if len(body.new_password) < 6:
        raise HTTPException(400, "新密码至少 6 位")
    if body.new_password == body.old_password:
        raise HTTPException(400, "新密码不能和原密码相同")

    stored = store.get_password_hash(user["user_id"])
    if not stored or not verify_password(body.old_password, stored):
        raise HTTPException(400, "原密码不正确")

    store.set_password(user["user_id"], hash_password(body.new_password))
    return {"status": "ok"}
