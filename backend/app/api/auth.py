"""用户注册、登录接口。"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import hash_password, verify_password, create_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterBody(BaseModel):
    username: str
    password: str


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(body: RegisterBody):
    username = body.username.strip()
    password = body.password

    if len(username) < 2:
        raise HTTPException(400, "用户名至少 2 个字符")
    if len(password) < 6:
        raise HTTPException(400, "密码至少 6 位")

    conn = get_db()
    cur = conn.cursor()

    # 检查用户名是否已存在
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(400, "用户名已存在")

    # 插入新用户
    cur.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, hash_password(password)),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()

    token = create_token(user_id, username)
    return {"token": token, "username": username, "user_id": user_id}


@router.post("/login")
def login(body: LoginBody):
    username = body.username.strip()
    password = body.password

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()

    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")

    token = create_token(row["id"], username)
    return {"token": token, "username": username, "user_id": row["id"]}


from fastapi import Depends
from app.core.auth import get_current_user


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    """测试用：返回当前登录用户的信息。需要带 Token 才能访问。"""
    return user