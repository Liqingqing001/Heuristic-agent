"""密码加密、JWT 生成/验证、登录态依赖。

密钥来源优先级：
1. 环境变量 ``SECRET_KEY``（生产环境推荐）；
2. ``backend/data/.secret_key``（首次启动自动生成，已 gitignore）；
3. 两者都没有时自动生成并写入文件，重启后 token 依然有效。
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt

from app.config import DATA_DIR
from app.core.db import get_conn

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

_SECRET_FILE = DATA_DIR / ".secret_key"
_secret_key: str | None = None


def _load_secret_key() -> str:
    global _secret_key
    if _secret_key:
        return _secret_key
    env_value = os.getenv("SECRET_KEY", "").strip()
    if env_value:
        _secret_key = env_value
        return _secret_key
    try:
        if _SECRET_FILE.exists():
            stored = _SECRET_FILE.read_text(encoding="utf-8").strip()
            if stored:
                _secret_key = stored
                return _secret_key
    except OSError:
        pass
    # 没有环境变量也没有文件：生成一个并落盘，避免每次重启把所有人踢下线
    generated = secrets.token_urlsafe(48)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _SECRET_FILE.write_text(generated, encoding="utf-8")
    except OSError:
        pass
    _secret_key = generated
    return _secret_key


def hash_password(password: str) -> str:
    """PBKDF2 加密，返回 'salt$hash'。"""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + "$" + pwd_hash.hex()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt_hex, hash_hex = hashed.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 100000)
        return actual == expected
    except Exception:
        return False


def create_token(user_id: int, username: str, role: str = "student") -> str:
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, _load_secret_key(), algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, _load_secret_key(), algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(authorization: str = Header(None)) -> dict:
    """解析 Authorization 头，并从库里取最新的角色。"""
    if not authorization:
        raise HTTPException(401, "未登录")
    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Token 无效或已过期")

    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, username, role, display_name FROM users WHERE id = ?",
            (payload.get("user_id"),),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(401, "用户不存在，请重新登录")
    return {
        "user_id": row["id"],
        "username": row["username"],
        "role": row["role"] or "student",
        "display_name": row["display_name"],
    }


def require_teacher(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "teacher":
        raise HTTPException(403, "仅教师可操作")
    return user
