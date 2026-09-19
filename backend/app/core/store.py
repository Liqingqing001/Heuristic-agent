"""对话持久化：用 SQLite 存储会话（conversations）与消息（messages），以及代码剖析记录。"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from app.config import DATA_DIR

DB_PATH = DATA_DIR / "chat.db"

DEFAULT_TITLE = "新会话"
DEFAULT_ANALYSIS_TITLE = "未命名剖析"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def _ensure_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 0,
            title TEXT NOT NULL DEFAULT '新会话',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS code_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT '未命名剖析',
            code TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'cpp',
            question TEXT,
            result TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    # 兼容旧库：conversations 表补 user_id
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()]
    if "user_id" not in cols:
        conn.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
    conn.commit()
    conn.close()


# ==================== 会话 ====================

def create_conversation(user_id: int, title: str = DEFAULT_TITLE) -> dict:
    _ensure_db()
    now = _now()
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, title or DEFAULT_TITLE, now, now),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return {"id": cid, "title": title or DEFAULT_TITLE, "created_at": now, "updated_at": now}


def list_conversations(user_id: int) -> list[dict]:
    _ensure_db()
    conn = _connect()
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM conversations "
        "WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def belongs_to_user(conversation_id: int, user_id: int) -> bool:
    _ensure_db()
    conn = _connect()
    row = conn.execute(
        "SELECT user_id FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    conn.close()
    return bool(row and row["user_id"] == user_id)


def get_messages(conversation_id: int, user_id: int | None = None) -> list[dict]:
    _ensure_db()
    conn = _connect()
    if user_id is not None and not belongs_to_user(conversation_id, user_id):
        conn.close()
        return []
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def add_message(conversation_id: int, role: str, content: str) -> None:
    _ensure_db()
    now = _now()
    conn = _connect()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, now),
    )
    conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
    conn.commit()
    conn.close()


def maybe_update_title(conversation_id: int, question: str) -> None:
    _ensure_db()
    conn = _connect()
    row = conn.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    if row and row["title"] in (DEFAULT_TITLE, ""):
        title = question.strip()[:30] or DEFAULT_TITLE
        conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))
        conn.commit()
    conn.close()


def delete_conversation(conversation_id: int, user_id: int) -> None:
    _ensure_db()
    conn = _connect()
    conn.execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )
    conn.commit()
    conn.close()


# ==================== 代码剖析 ====================

def create_code_analysis(user_id: int, code: str, language: str, question: str | None) -> dict:
    """创建一条空的剖析记录，返回 id。结果稍后由流式过程写入。"""
    _ensure_db()
    now = _now()
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO code_analyses (user_id, title, code, language, question, result, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, '', ?, ?)",
        (user_id, DEFAULT_ANALYSIS_TITLE, code, language, question, now, now),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return {"id": cid, "title": DEFAULT_ANALYSIS_TITLE, "created_at": now}


def update_code_analysis_result(analysis_id: int, user_id: int, result: str, code: str, question: str | None) -> None:
    """剖析完成后写入完整结果，并根据首行自动命名。"""
    _ensure_db()
    now = _now()
    conn = _connect()
    row = conn.execute(
        "SELECT title FROM code_analyses WHERE id = ? AND user_id = ?",
        (analysis_id, user_id),
    ).fetchone()
    if not row:
        conn.close()
        return
    title = row["title"]
    if title in (DEFAULT_ANALYSIS_TITLE, ""):
        head = (question or "").strip() or code.strip().split("\n")[0]
        title = head[:20] or DEFAULT_ANALYSIS_TITLE
    conn.execute(
        "UPDATE code_analyses SET result = ?, title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (result, title, now, analysis_id, user_id),
    )
    conn.commit()
    conn.close()


def list_code_analyses(user_id: int) -> list[dict]:
    """列出当前用户的所有剖析记录（不含代码全文和结果，只为列表显示）。"""
    _ensure_db()
    conn = _connect()
    rows = conn.execute(
        "SELECT id, title, language, created_at, updated_at FROM code_analyses "
        "WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_code_analysis(analysis_id: int, user_id: int) -> dict | None:
    """获取单条剖析详情（含代码与结果）。只返回属于该用户的。"""
    _ensure_db()
    conn = _connect()
    row = conn.execute(
        "SELECT id, title, code, language, question, result, created_at, updated_at "
        "FROM code_analyses WHERE id = ? AND user_id = ?",
        (analysis_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_code_analysis(analysis_id: int, user_id: int) -> None:
    _ensure_db()
    conn = _connect()
    conn.execute(
        "DELETE FROM code_analyses WHERE id = ? AND user_id = ?",
        (analysis_id, user_id),
    )
    conn.commit()
    conn.close()