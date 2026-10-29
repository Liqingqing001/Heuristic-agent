"""兼容旧导入：数据库逻辑已合并到 :mod:`app.core.db`。

新代码请直接 ``from app.core.db import get_conn, init_db``。
"""
from app.core.db import DB_PATH, get_conn, init_db

# 旧名字，保留给早期代码/脚本
get_db = get_conn

__all__ = ["DB_PATH", "get_conn", "get_db", "init_db"]
