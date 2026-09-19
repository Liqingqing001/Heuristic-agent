"""SQLite 数据库连接与初始化。"""
import sqlite3
from pathlib import Path

# 数据库文件位置：backend/data/app.db
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "app.db"


def get_db():
    """获取数据库连接（每次调用返回新连接，用完手动 close）。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # 让查询结果可以按列名访问
    return conn


def init_db():
    """初始化数据库表（幂等，重复调用不会报错）。"""
    conn = get_db()
    cur = conn.cursor()

    # 用户表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 会话表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT '新会话',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # 消息表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)

    conn.commit()
    conn.close()