"""用户注册、登录接口。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import create_token, get_current_user, hash_password, verify_password
from app.core.db import get_conn

router = APIRouter(prefix="/api/auth", tags=["auth"])

VALID_ROLES = {"student", "teacher"}


class RegisterBody(BaseModel):
    username: str
    password: str
    role: str = "student"
    display_name: str | None = None


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(body: RegisterBody):
    username = body.username.strip()
    password = body.password
    role = body.role if body.role in VALID_ROLES else "student"
    display_name = (body.display_name or "").strip() or username

    if len(username) < 2:
        raise HTTPException(400, "用户名至少 2 个字符")
    if len(password) < 6:
        raise HTTPException(400, "密码至少 6 位")

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            raise HTTPException(400, "用户名已存在")

        cur.execute(
            "INSERT INTO users (username, password_hash, role, display_name) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), role, display_name),
        )
        conn.commit()
        user_id = cur.lastrowid
    finally:
        conn.close()

    token = create_token(user_id, username, role)
    return {
        "token": token,
        "username": username,
        "user_id": user_id,
        "role": role,
        "display_name": display_name,
    }


@router.post("/login")
def login(body: LoginBody):
    username = body.username.strip()
    password = body.password

    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, role, display_name FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        conn.close()

    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")

    role = row["role"] or "student"
    token = create_token(row["id"], row["username"], role)
    return {
        "token": token,
        "username": row["username"],
        "user_id": row["id"],
        "role": role,
        "display_name": row["display_name"] or row["username"],
    }


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    """返回当前登录用户的信息（需要带 Token）。"""
    return user
