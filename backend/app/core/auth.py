"""密码加密 + JWT Token 生成/验证。"""
import hashlib
import os
from datetime import datetime, timedelta
from jose import jwt, JWTError

SECRET_KEY = "your-secret-key-change-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """用 PBKDF2 加密密码，返回 'salt$hash' 格式"""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + "$" + pwd_hash.hex()


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码是否匹配"""
    try:
        salt_hex, hash_hex = hashed.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 100000)
        return actual == expected
    except Exception:
        return False


def create_token(user_id: int, username: str) -> str:
    """生成 JWT Token"""
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    """解码 Token，失败返回 None"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


from fastapi import Header, HTTPException


def get_current_user(authorization: str = Header(None)):
    """从请求头 Authorization 中解析 JWT，返回用户信息。
    用法：在路由函数参数里写 user = Depends(get_current_user)
    """
    if not authorization:
        raise HTTPException(401, "未登录")
    # 格式通常是 "Bearer eyJhbGci..."
    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Token 无效或已过期")
    return {"user_id": payload["user_id"], "username": payload["username"]}