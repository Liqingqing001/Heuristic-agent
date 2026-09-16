"""对话持久化：用 SQLite 存储会话（conversations）与消息（messages）。"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from app.config import DATA_DIR

DB_PATH = DATA_DIR / "chat.db"

DEFAULT_TITLE = "新会话"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _connect() -> sqlite3.Connection:
    # timeout + busy_timeout：写锁冲突时等待而非立即报 "database is locked"
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def _ensure_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    # WAL 模式：读写不互斥，显著降低锁冲突
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        """
    )
    conn.commit()
    conn.close()


def create_conversation(title: str = DEFAULT_TITLE) -> dict:
    _ensure_db()
    now = _now()
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
        (title or DEFAULT_TITLE, now, now),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return {"id": cid, "title": title or DEFAULT_TITLE, "created_at": now, "updated_at": now}


def list_conversations() -> list[dict]:
    _ensure_db()
    conn = _connect()
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC, id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_messages(conversation_id: int) -> list[dict]:
    _ensure_db()
    conn = _connect()
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
    """若标题仍是默认值，用首条问题自动命名（截前 30 字）。"""
    _ensure_db()
    conn = _connect()
    row = conn.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
    if row and row["title"] in (DEFAULT_TITLE, ""):
        title = question.strip()[:30] or DEFAULT_TITLE
        conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))
        conn.commit()
    conn.close()


def delete_conversation(conversation_id: int) -> None:
    _ensure_db()
    conn = _connect()
    conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()
