"""统一的 SQLite 连接、建表与旧库迁移。

数据库文件：``backend/data/app.db``（WAL 模式）。

历史版本把用户放在 app.db、把会话放在 chat.db，并用两套连接代码维护。
从本版本起统一为一个库；首次启动时会把 chat.db 里的会话/消息/剖析记录
复制过来（按 id 幂等），原文件保留不删，方便回退。
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from app.config import DATA_DIR

# 测试时可用 APP_DB_PATH 指向临时库，避免污染开发数据
DB_PATH = Path(os.getenv("APP_DB_PATH", str(DATA_DIR / "app.db")))
LEGACY_CHAT_DB = DATA_DIR / "chat.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    display_name TEXT,
    real_name TEXT DEFAULT '',
    school TEXT DEFAULT '',
    department TEXT DEFAULT '',
    major TEXT DEFAULT '',
    gender TEXT DEFAULT '',
    enrollment_year TEXT DEFAULT '',
    bio TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
    diagnosis TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    teacher_id INTEGER NOT NULL,
    term TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS class_members (
    class_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TEXT NOT NULL,
    PRIMARY KEY (class_id, user_id),
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL DEFAULT 'code',
    kp_ids TEXT NOT NULL DEFAULT '',
    due_at TEXT,
    allow_late INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'cpp',
    status TEXT NOT NULL DEFAULT 'submitted',
    score REAL,
    feedback TEXT NOT NULL DEFAULT '',
    graded_at TEXT NOT NULL DEFAULT '',
    graded_by INTEGER NOT NULL DEFAULT 0,
    ai_result TEXT NOT NULL DEFAULT '',
    diagnosis TEXT NOT NULL DEFAULT '',
    submitted_at TEXT NOT NULL,
    UNIQUE (assignment_id, user_id),
    FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS kp_mastery (
    user_id INTEGER NOT NULL,
    kp_id TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    score REAL NOT NULL DEFAULT 50,
    last_hint INTEGER,
    last_severity TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, kp_id)
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_code_analyses_user ON code_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_class_members_user ON class_members(user_id);
CREATE INDEX IF NOT EXISTS idx_assignments_class ON assignments(class_id);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_user ON submissions(user_id);
"""


def get_conn() -> sqlite3.Connection:
    """新连接（调用方负责 close）。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> bool:
    if column in _columns(conn, table):
        return False
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
    return True


def _meta_get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def init_db() -> dict:
    """建表 + 兼容旧库 + 迁移 chat.db（幂等）。"""
    conn = get_conn()
    result = {"migrated": {}, "added_columns": []}
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        conn.executescript(_INDEXES)

        # 旧版本 users 表没有 role / display_name
        if _ensure_column(conn, "users", "role", "TEXT NOT NULL DEFAULT 'student'"):
            result["added_columns"].append("users.role")
        if _ensure_column(conn, "users", "display_name", "TEXT"):
            result["added_columns"].append("users.display_name")
        # 个人资料页字段
        for column in ("real_name", "school", "department", "major", "gender", "enrollment_year", "bio"):
            if _ensure_column(conn, "users", column, "TEXT DEFAULT ''"):
                result["added_columns"].append(f"users.{column}")
        # 更早版本的 conversations 表没有 updated_at
        if _ensure_column(conn, "conversations", "updated_at", "TEXT NOT NULL DEFAULT ''"):
            result["added_columns"].append("conversations.updated_at")
        # 旧版本 code_analyses 没有结构化诊断
        if _ensure_column(conn, "code_analyses", "diagnosis", "TEXT NOT NULL DEFAULT ''"):
            result["added_columns"].append("code_analyses.diagnosis")
        # 批阅相关字段
        for column, ddl in (
            ("feedback", "TEXT NOT NULL DEFAULT ''"),
            ("graded_at", "TEXT NOT NULL DEFAULT ''"),
            ("graded_by", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if _ensure_column(conn, "submissions", column, ddl):
                result["added_columns"].append(f"submissions.{column}")
        # 任务是否允许逾期提交（默认允许，保持旧行为）
        if _ensure_column(conn, "assignments", "allow_late", "INTEGER NOT NULL DEFAULT 1"):
            result["added_columns"].append("assignments.allow_late")

        conn.commit()
        try:
            result["migrated"] = _migrate_legacy_chat_db(conn)
        except Exception as exc:  # 迁移失败不影响启动，旧库原样保留
            result["migrated"] = {"error": str(exc)}
        conn.commit()
    finally:
        conn.close()
    return result


def _migrate_legacy_chat_db(conn: sqlite3.Connection) -> dict:
    """把 chat.db 的会话/消息/剖析记录复制进 app.db，只做一次。"""
    if _meta_get(conn, "legacy_chat_migrated") == "1":
        return {"skipped": True}
    if not LEGACY_CHAT_DB.exists():
        _meta_set(conn, "legacy_chat_migrated", "1")
        return {"skipped": True, "reason": "no chat.db"}

    counts = {"conversations": 0, "messages": 0, "code_analyses": 0}
    # 批量搬运期间关闭外键检查，避免历史脏数据（孤儿消息）卡住迁移
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("ATTACH DATABASE ? AS legacy", (str(LEGACY_CHAT_DB),))
        try:
            # ATTACH 之后 sqlite_master 只包含 main，旧库的表要单独查
            legacy_tables = {
                row[0]
                for row in conn.execute("SELECT name FROM legacy.sqlite_master WHERE type = 'table'")
            }

            if "conversations" in legacy_tables:
                legacy_cols = {
                    row[1] for row in conn.execute("PRAGMA legacy.table_info(conversations)")
                }
                has_user = "user_id" in legacy_cols
                has_updated = "updated_at" in legacy_cols
                user_expr = "COALESCE(user_id, 0)" if has_user else "0"
                updated_expr = "COALESCE(updated_at, created_at, '')" if has_updated else "COALESCE(created_at, '')"
                cur = conn.execute(
                    f"INSERT OR IGNORE INTO conversations (id, user_id, title, created_at, updated_at) "
                    f"SELECT id, {user_expr}, COALESCE(title, '新会话'), COALESCE(created_at, ''), {updated_expr} "
                    f"FROM legacy.conversations"
                )
                counts["conversations"] = cur.rowcount

            if "messages" in legacy_tables:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO messages (id, conversation_id, role, content, created_at) "
                    "SELECT id, conversation_id, role, content, COALESCE(created_at, '') FROM legacy.messages"
                )
                counts["messages"] = cur.rowcount

            if "code_analyses" in legacy_tables:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO code_analyses "
                    "(id, user_id, title, code, language, question, result, created_at, updated_at) "
                    "SELECT id, user_id, COALESCE(title, '未命名剖析'), code, COALESCE(language, 'cpp'), "
                    "question, COALESCE(result, ''), COALESCE(created_at, ''), COALESCE(updated_at, created_at, '') "
                    "FROM legacy.code_analyses"
                )
                counts["code_analyses"] = cur.rowcount

            conn.commit()
        finally:
            conn.execute("DETACH DATABASE legacy")
    finally:
        conn.execute("PRAGMA foreign_keys = ON")

    _meta_set(conn, "legacy_chat_migrated", "1")
    return counts
