"""数据访问层：会话、消息、代码剖析、班级、任务、提交。

所有数据统一存在 ``backend/data/app.db``（见 :mod:`app.core.db`）。
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timedelta

from app.core.db import get_conn, init_db

DEFAULT_TITLE = "新会话"
DEFAULT_ANALYSIS_TITLE = "未命名剖析"

_CLASS_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_ready = False


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _is_overdue(due_at: str | None) -> bool:
    if not due_at:
        return False
    text = str(due_at).strip().replace("/", "-").replace(" ", "T")
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt) < datetime.now()
        except ValueError:
            continue
    return False


def _ensure() -> None:
    """进程内只初始化一次（init_db 本身幂等）。"""
    global _ready
    if not _ready:
        init_db()
        _ready = True


def _rows(rows) -> list[dict]:
    return [dict(row) for row in rows]


# ==================== 会话 ====================

def create_conversation(user_id: int, title: str = DEFAULT_TITLE) -> dict:
    _ensure()
    now = _now()
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, title or DEFAULT_TITLE, now, now),
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "title": title or DEFAULT_TITLE,
            "created_at": now,
            "updated_at": now,
        }
    finally:
        conn.close()


def list_conversations(user_id: int) -> list[dict]:
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations "
            "WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
            (user_id,),
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def belongs_to_user(conversation_id: int, user_id: int) -> bool:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT user_id FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return bool(row and row["user_id"] == user_id)
    finally:
        conn.close()


def get_messages(conversation_id: int, user_id: int | None = None) -> list[dict]:
    _ensure()
    if user_id is not None and not belongs_to_user(conversation_id, user_id):
        return []
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def add_message(conversation_id: int, role: str, content: str) -> None:
    _ensure()
    now = _now()
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, now),
        )
        conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
        conn.commit()
    finally:
        conn.close()


def maybe_update_title(conversation_id: int, question: str) -> None:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute("SELECT title FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if row and row["title"] in (DEFAULT_TITLE, ""):
            title = question.strip()[:30] or DEFAULT_TITLE
            conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conversation_id))
            conn.commit()
    finally:
        conn.close()


def delete_conversation(conversation_id: int, user_id: int) -> None:
    """删除会话及其消息。

    注意：早期版本的 messages 表没有 ON DELETE CASCADE，这里显式先删消息，
    否则删除父记录会触发外键约束错误。
    """
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            return
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


# ==================== 代码剖析 ====================

def create_code_analysis(user_id: int, code: str, language: str, question: str | None) -> dict:
    """创建一条空的剖析记录，结果稍后由流式过程写入。"""
    _ensure()
    now = _now()
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO code_analyses (user_id, title, code, language, question, result, diagnosis, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, '', '', ?, ?)",
            (user_id, DEFAULT_ANALYSIS_TITLE, code, language, question, now, now),
        )
        conn.commit()
        return {"id": cur.lastrowid, "title": DEFAULT_ANALYSIS_TITLE, "created_at": now}
    finally:
        conn.close()


def update_code_analysis_result(
    analysis_id: int,
    user_id: int,
    result: str,
    code: str,
    question: str | None,
    diagnosis: dict | None = None,
) -> None:
    """剖析完成后写入完整结果（含结构化诊断），并根据首行自动命名。"""
    _ensure()
    now = _now()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT title FROM code_analyses WHERE id = ? AND user_id = ?",
            (analysis_id, user_id),
        ).fetchone()
        if not row:
            return
        title = row["title"]
        if title in (DEFAULT_ANALYSIS_TITLE, ""):
            head = (question or "").strip() or code.strip().split("\n")[0]
            title = head[:20] or DEFAULT_ANALYSIS_TITLE
        conn.execute(
            "UPDATE code_analyses SET result = ?, title = ?, diagnosis = ?, updated_at = ? "
            "WHERE id = ? AND user_id = ?",
            (result, title, json.dumps(diagnosis or {}, ensure_ascii=False), now, analysis_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_code_analyses(user_id: int) -> list[dict]:
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, title, language, created_at, updated_at FROM code_analyses "
            "WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
            (user_id,),
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def get_code_analysis(analysis_id: int, user_id: int) -> dict | None:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, title, code, language, question, result, diagnosis, created_at, updated_at "
            "FROM code_analyses WHERE id = ? AND user_id = ?",
            (analysis_id, user_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_code_analysis(analysis_id: int, user_id: int) -> None:
    _ensure()
    conn = get_conn()
    try:
        conn.execute(
            "DELETE FROM code_analyses WHERE id = ? AND user_id = ?",
            (analysis_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


# ==================== 班级 ====================

def _generate_class_code(conn: sqlite3.Connection) -> str:
    for _ in range(30):
        code = "".join(secrets.choice(_CLASS_CODE_ALPHABET) for _ in range(6))
        exists = conn.execute("SELECT 1 FROM classes WHERE code = ?", (code,)).fetchone()
        if not exists:
            return code
    raise RuntimeError("班级邀请码生成失败，请重试")


def assignment_closed(assignment: dict | None) -> bool:
    """任务是否已截止且不允许迟交。"""
    if not assignment:
        return False
    return _is_overdue(assignment.get("due_at")) and not int(assignment.get("allow_late", 1) or 0)


def create_class(teacher_id: int, name: str, term: str = "") -> dict:
    _ensure()
    now = _now()
    conn = get_conn()
    try:
        code = _generate_class_code(conn)
        cur = conn.execute(
            "INSERT INTO classes (name, code, teacher_id, term, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, code, teacher_id, term, now),
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "name": name,
            "code": code,
            "teacher_id": teacher_id,
            "term": term,
            "created_at": now,
            "member_count": 0,
        }
    finally:
        conn.close()


def list_classes_taught(teacher_id: int) -> list[dict]:
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT c.*, (SELECT COUNT(*) FROM class_members m WHERE m.class_id = c.id) AS member_count "
            "FROM classes c WHERE c.teacher_id = ? ORDER BY c.id DESC",
            (teacher_id,),
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def list_classes_joined(user_id: int) -> list[dict]:
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT c.*, u.username AS teacher_name, "
            "  (SELECT COUNT(*) FROM class_members m2 WHERE m2.class_id = c.id) AS member_count "
            "FROM classes c "
            "JOIN class_members m ON m.class_id = c.id AND m.user_id = ? "
            "LEFT JOIN users u ON u.id = c.teacher_id "
            "ORDER BY c.id DESC",
            (user_id,),
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def get_class(class_id: int) -> dict | None:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT c.*, u.username AS teacher_name, "
            "  (SELECT COUNT(*) FROM class_members m WHERE m.class_id = c.id) AS member_count "
            "FROM classes c LEFT JOIN users u ON u.id = c.teacher_id WHERE c.id = ?",
            (class_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_class_by_code(code: str) -> dict | None:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM classes WHERE code = ?", (code.strip().upper(),)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def is_member(class_id: int, user_id: int) -> bool:
    _ensure()
    conn = get_conn()
    try:
        return bool(
            conn.execute(
                "SELECT 1 FROM class_members WHERE class_id = ? AND user_id = ?",
                (class_id, user_id),
            ).fetchone()
        )
    finally:
        conn.close()


def join_class(code: str, user_id: int) -> dict:
    """返回 {status: joined|already|not_found, class?}。"""
    _ensure()
    cls = get_class_by_code(code)
    if not cls:
        return {"status": "not_found"}
    if cls["teacher_id"] == user_id:
        return {"status": "is_teacher", "class": cls}
    if is_member(cls["id"], user_id):
        return {"status": "already", "class": cls}
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
            (cls["id"], user_id, _now()),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "joined", "class": get_class(cls["id"])}


def list_members(class_id: int) -> list[dict]:
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT u.id AS user_id, u.username, u.display_name, m.joined_at "
            "FROM class_members m JOIN users u ON u.id = m.user_id "
            "WHERE m.class_id = ? ORDER BY m.joined_at ASC",
            (class_id,),
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


# ==================== 任务 ====================

def create_assignment(
    class_id: int,
    title: str,
    description: str = "",
    type_: str = "code",
    kp_ids: list[str] | None = None,
    due_at: str | None = None,
    created_by: int = 0,
    allow_late: int = 1,
) -> dict:
    _ensure()
    now = _now()
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO assignments (class_id, title, description, type, kp_ids, due_at, allow_late, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                class_id,
                title,
                description,
                type_,
                ",".join(kp_ids or []),
                due_at,
                1 if allow_late else 0,
                created_by,
                now,
            ),
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "class_id": class_id,
            "title": title,
            "description": description,
            "type": type_,
            "kp_ids": kp_ids or [],
            "due_at": due_at,
            "allow_late": 1 if allow_late else 0,
            "created_at": now,
        }
    finally:
        conn.close()


def list_assignments(class_id: int, user_id: int | None = None) -> list[dict]:
    """user_id 不为空时附带该学生的提交状态。"""
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT a.*, "
            "  (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id = a.id) AS submitted_count, "
            "  (SELECT COUNT(*) FROM class_members m WHERE m.class_id = a.class_id) AS member_count "
            "FROM assignments a WHERE a.class_id = ? ORDER BY a.id DESC",
            (class_id,),
        ).fetchall()
        items = _rows(rows)
        titles = _kp_titles()
        for item in items:
            item["kp_ids"] = [k for k in (item.get("kp_ids") or "").split(",") if k]
            item["kp_titles"] = {
                kp_id: (titles.get(kp_id, {}) or {}).get("title", "") for kp_id in item["kp_ids"]
            }
            item["submitted_count"] = item.get("submitted_count", 0)
            item["member_count"] = item.get("member_count", 0)
            item["is_overdue"] = _is_overdue(item.get("due_at"))
            item["my_submission"] = None
        if user_id is not None:
            mine = conn.execute(
                "SELECT id, assignment_id, status, score, feedback, graded_at, submitted_at FROM submissions "
                "WHERE user_id = ? AND assignment_id IN (SELECT id FROM assignments WHERE class_id = ?)",
                (user_id, class_id),
            ).fetchall()
            by_assignment = {row["assignment_id"]: dict(row) for row in mine}
            for item in items:
                item["my_submission"] = by_assignment.get(item["id"])
        return items
    finally:
        conn.close()


def get_assignment(assignment_id: int) -> dict | None:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["kp_ids"] = [k for k in (item.get("kp_ids") or "").split(",") if k]
        titles = _kp_titles()
        item["kp_titles"] = {
            kp_id: (titles.get(kp_id, {}) or {}).get("title", "") for kp_id in item["kp_ids"]
        }
        return item
    finally:
        conn.close()


def update_assignment(assignment_id: int, fields: dict) -> dict | None:
    """教师编辑任务：标题、说明、类型、知识点、截止时间、是否允许迟交。"""
    _ensure()
    allowed = {"title", "description", "type", "kp_ids", "due_at", "allow_late"}
    updates = {}
    for key, value in fields.items():
        if key not in allowed:
            continue
        if key == "kp_ids":
            updates[key] = ",".join(value or [])
        elif key == "allow_late":
            updates[key] = 1 if value else 0
        else:
            updates[key] = value

    if updates:
        assignments = ", ".join(f"{key} = ?" for key in updates)
        conn = get_conn()
        try:
            conn.execute(
                f"UPDATE assignments SET {assignments} WHERE id = ?",
                (*list(updates.values()), assignment_id),
            )
            conn.commit()
        finally:
            conn.close()
    return get_assignment(assignment_id)


def delete_assignment(assignment_id: int) -> None:
    """删除任务（提交记录通过外键级联删除）。"""
    _ensure()
    conn = get_conn()
    try:
        conn.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
        conn.commit()
    finally:
        conn.close()


def student_detail(class_id: int, user_id: int) -> dict | None:
    """教师查看某个学生的档案：资料 + 本班提交记录 + 知识点掌握度。"""
    _ensure()
    if not is_member(class_id, user_id):
        return None
    conn = get_conn()
    try:
        profile = conn.execute(
            "SELECT id, username, display_name, real_name, school, department, major, "
            "gender, enrollment_year, bio, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not profile:
            return None
        submissions = conn.execute(
            "SELECT s.id, s.assignment_id, s.status, s.score, s.feedback, s.submitted_at, "
            "       s.diagnosis, a.title AS assignment_title, a.type AS assignment_type "
            "FROM submissions s JOIN assignments a ON a.id = s.assignment_id "
            "WHERE a.class_id = ? AND s.user_id = ? ORDER BY s.submitted_at DESC",
            (class_id, user_id),
        ).fetchall()
    finally:
        conn.close()

    mastery = [item for item in mastery_for_user(user_id)]
    return {
        "profile": dict(profile),
        "submissions": [dict(row) for row in submissions],
        "mastery": mastery,
    }


def class_export_rows(class_id: int) -> list[dict]:
    """成绩单数据（CSV 导出用）。"""
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT u.username, u.display_name, u.real_name, a.title AS assignment, a.type, "
            "       s.status, s.score, s.feedback, s.submitted_at "
            "FROM submissions s "
            "JOIN assignments a ON a.id = s.assignment_id "
            "JOIN users u ON u.id = s.user_id "
            "WHERE a.class_id = ? ORDER BY u.username, a.id",
            (class_id,),
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


# ==================== 提交 ====================

def upsert_submission(
    assignment_id: int,
    user_id: int,
    content: str,
    language: str = "cpp",
    status: str = "analyzed",
    ai_result: str = "",
    diagnosis: dict | None = None,
) -> int:
    _ensure()
    now = _now()
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO submissions "
            "(assignment_id, user_id, content, language, status, ai_result, diagnosis, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(assignment_id, user_id) DO UPDATE SET "
            "content = excluded.content, language = excluded.language, status = excluded.status, "
            "ai_result = excluded.ai_result, diagnosis = excluded.diagnosis, submitted_at = excluded.submitted_at, "
            "score = NULL, feedback = '', graded_at = '', graded_by = 0",
            (
                assignment_id,
                user_id,
                content,
                language,
                status,
                ai_result,
                json.dumps(diagnosis or {}, ensure_ascii=False),
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM submissions WHERE assignment_id = ? AND user_id = ?",
            (assignment_id, user_id),
        ).fetchone()
        return row["id"] if row else 0
    finally:
        conn.close()


def list_submissions(assignment_id: int) -> list[dict]:
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT s.id, s.user_id, s.language, s.status, s.score, s.feedback, s.graded_at, "
            "       s.submitted_at, s.diagnosis, u.username, u.display_name "
            "FROM submissions s JOIN users u ON u.id = s.user_id "
            "WHERE s.assignment_id = ? ORDER BY s.submitted_at ASC",
            (assignment_id,),
        ).fetchall()
        return _rows(rows)
    finally:
        conn.close()


def get_submission(submission_id: int) -> dict | None:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT s.*, u.username, u.display_name FROM submissions s "
            "JOIN users u ON u.id = s.user_id WHERE s.id = ?",
            (submission_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def grade_submission(
    submission_id: int,
    teacher_id: int,
    score: float,
    feedback: str = "",
    returned: bool = False,
) -> dict | None:
    """教师批阅：打分、写评语，或退回重做。"""
    _ensure()
    submission = get_submission(submission_id)
    if not submission:
        return None
    assignment = get_assignment(submission["assignment_id"])
    if not assignment or not is_teacher_of_class(assignment["class_id"], teacher_id):
        return None

    status = "returned" if returned else "graded"
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE submissions SET score = ?, feedback = ?, status = ?, graded_at = ?, graded_by = ? "
            "WHERE id = ?",
            (score, feedback.strip(), status, _now(), teacher_id, submission_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_submission(submission_id)


# ==================== 知识点掌握度 ====================

def record_mastery(user_id: int, kp_ids: list[str] | None, hint: int | None, severity: str | None) -> None:
    """每次诊断后按知识点累加掌握度：提示层级越浅、严重度越低，得分越高。"""
    ids = [kp_id for kp_id in (kp_ids or []) if kp_id]
    if not ids:
        return
    _ensure()
    delta = {1: 15, 2: 5, 3: -10}.get(hint, 0)
    if severity == "high":
        delta -= 5
    elif severity == "low":
        delta += 3
    now = _now()
    start = max(0, min(100, 50 + delta))
    conn = get_conn()
    try:
        for kp_id in ids:
            conn.execute(
                "INSERT INTO kp_mastery (user_id, kp_id, attempts, score, last_hint, last_severity, updated_at) "
                "VALUES (?, ?, 1, ?, ?, ?, ?) "
                "ON CONFLICT(user_id, kp_id) DO UPDATE SET "
                "  attempts = attempts + 1, "
                "  score = max(0, min(100, score + ?)), "
                "  last_hint = excluded.last_hint, "
                "  last_severity = excluded.last_severity, "
                "  updated_at = excluded.updated_at",
                (user_id, kp_id, start, hint, severity or "", now, delta),
            )
        conn.commit()
    finally:
        conn.close()


def _kp_titles() -> dict[str, dict]:
    """知识点编号 -> 标题/章节（读文件，量小，直接读）。"""
    from app.config import KNOWLEDGE_DIR
    from app.utils import kp_meta

    titles: dict[str, dict] = {}
    for path in kp_meta.iter_kp_files(KNOWLEDGE_DIR / "kp"):
        try:
            kp = kp_meta.load_kp(path)
        except Exception:
            continue
        meta = kp["meta"]
        if meta.get("id"):
            titles[str(meta["id"])] = {
                "title": str(meta.get("title") or ""),
                "chapter": meta.get("chapter"),
            }
    return titles


def mastery_for_user(user_id: int) -> list[dict]:
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT kp_id, attempts, score, last_hint, last_severity, updated_at "
            "FROM kp_mastery WHERE user_id = ? ORDER BY score ASC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    titles = _kp_titles()
    items = []
    for row in rows:
        info = titles.get(row["kp_id"], {})
        items.append({
            "kp_id": row["kp_id"],
            "title": info.get("title", ""),
            "chapter": info.get("chapter"),
            "attempts": row["attempts"],
            "score": round(row["score"], 1),
            "last_hint": row["last_hint"],
            "last_severity": row["last_severity"],
            "updated_at": row["updated_at"],
        })
    return items


def class_mastery(class_id: int) -> list[dict]:
    """班级知识点掌握度：按知识点聚合成员平均分，弱的排前面。"""
    _ensure()
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT m.kp_id, AVG(m.score) AS avg_score, SUM(m.attempts) AS attempts, "
            "       COUNT(DISTINCT m.user_id) AS student_count "
            "FROM kp_mastery m "
            "JOIN class_members cm ON cm.user_id = m.user_id AND cm.class_id = ? "
            "GROUP BY m.kp_id ORDER BY avg_score ASC",
            (class_id,),
        ).fetchall()
    finally:
        conn.close()
    titles = _kp_titles()
    items = []
    for row in rows:
        info = titles.get(row["kp_id"], {})
        items.append({
            "kp_id": row["kp_id"],
            "title": info.get("title", ""),
            "chapter": info.get("chapter"),
            "avg_score": round(row["avg_score"], 1),
            "attempts": row["attempts"],
            "student_count": row["student_count"],
        })
    return items


def is_teacher_of_class(class_id: int, user_id: int) -> bool:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM classes WHERE id = ? AND teacher_id = ?", (class_id, user_id)
        ).fetchone()
        return bool(row)
    finally:
        conn.close()


# ==================== 学情看板 ====================

def class_overview(class_id: int) -> dict:
    """教师看板：提交率、未交名单、错因分布。"""
    _ensure()
    cls = get_class(class_id)
    if not cls:
        return {}
    members = list_members(class_id)
    assignments = list_assignments(class_id)

    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT s.*, u.username, u.display_name, a.title AS assignment_title "
            "FROM submissions s "
            "JOIN assignments a ON a.id = s.assignment_id "
            "JOIN users u ON u.id = s.user_id "
            "WHERE a.class_id = ? ORDER BY s.submitted_at DESC",
            (class_id,),
        ).fetchall()
        submissions = _rows(rows)
    finally:
        conn.close()

    # 每个学生的提交进度
    total_assignments = len(assignments)
    submitted_map: dict[int, set[int]] = {}
    for sub in submissions:
        submitted_map.setdefault(sub["user_id"], set()).add(sub["assignment_id"])

    students = []
    for member in members:
        done_ids = submitted_map.get(member["user_id"], set())
        students.append({
            "user_id": member["user_id"],
            "username": member["username"],
            "display_name": member["display_name"],
            "submitted": len(done_ids),
            "total": total_assignments,
            "rate": round(len(done_ids) / total_assignments, 3) if total_assignments else 0.0,
            "missing": [a["title"] for a in assignments if a["id"] not in done_ids],
        })

    # 错因分布
    error_counter: dict[str, int] = {}
    severity_counter: dict[str, int] = {}
    for sub in submissions:
        diag = _load_json(sub.get("diagnosis"))
        for error_type in diag.get("error_types", []) or []:
            error_counter[str(error_type)] = error_counter.get(str(error_type), 0) + 1
        severity = diag.get("severity")
        if severity:
            severity_counter[str(severity)] = severity_counter.get(str(severity), 0) + 1

    assignment_rows = []
    for assignment in sorted(assignments, key=lambda item: item["id"]):
        submitted = sum(1 for sub in submissions if sub["assignment_id"] == assignment["id"])
        assignment_rows.append({
            "id": assignment["id"],
            "title": assignment["title"],
            "type": assignment["type"],
            "due_at": assignment["due_at"],
            "is_overdue": _is_overdue(assignment["due_at"]),
            "submitted": submitted,
            "member_count": len(members),
            "rate": round(submitted / len(members), 3) if members else 0.0,
        })

    # 近 14 天提交趋势
    day_counter: dict[str, int] = {}
    for sub in submissions:
        day = str(sub.get("submitted_at", ""))[:10]
        if day:
            day_counter[day] = day_counter.get(day, 0) + 1
    today = datetime.now().date()
    trend = [
        {
            "date": (today - timedelta(days=offset)).isoformat(),
            "count": day_counter.get((today - timedelta(days=offset)).isoformat(), 0),
        }
        for offset in range(13, -1, -1)
    ]

    # 分数段分布（已批阅）
    buckets = [
        {"label": "0-59", "count": 0},
        {"label": "60-69", "count": 0},
        {"label": "70-79", "count": 0},
        {"label": "80-89", "count": 0},
        {"label": "90-100", "count": 0},
    ]
    for sub in submissions:
        score = sub.get("score")
        if score is None:
            continue
        if score < 60:
            buckets[0]["count"] += 1
        elif score < 70:
            buckets[1]["count"] += 1
        elif score < 80:
            buckets[2]["count"] += 1
        elif score < 90:
            buckets[3]["count"] += 1
        else:
            buckets[4]["count"] += 1

    return {
        "class": cls,
        "member_count": len(members),
        "assignment_count": total_assignments,
        "assignments": assignment_rows,
        "students": sorted(students, key=lambda item: item["rate"]),
        "error_distribution": sorted(
            ({"type": key, "count": value} for key, value in error_counter.items()),
            key=lambda item: -item["count"],
        ),
        "severity_distribution": sorted(
            ({"level": key, "count": value} for key, value in severity_counter.items()),
            key=lambda item: -item["count"],
        ),
        "pending_grading": sum(
            1 for sub in submissions if sub.get("status") in ("submitted", "analyzed")
        ),
        "graded_count": sum(1 for sub in submissions if sub.get("status") == "graded"),
        "trend": trend,
        "score_distribution": buckets,
        "recent_submissions": [
            {
                "id": sub["id"],
                "assignment_id": sub["assignment_id"],
                "assignment_title": sub["assignment_title"],
                "username": sub["username"],
                "display_name": sub.get("display_name"),
                "submitted_at": sub["submitted_at"],
                "status": sub["status"],
                "score": sub.get("score"),
            }
            for sub in submissions[:10]
        ],
    }


def _load_json(text: str | None) -> dict:
    if not text:
        return {}
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


# ==================== 个人资料 ====================

PROFILE_FIELDS = (
    "display_name",
    "real_name",
    "school",
    "department",
    "major",
    "gender",
    "enrollment_year",
    "bio",
)


def get_profile(user_id: int) -> dict | None:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, username, role, display_name, real_name, school, department, major, "
            "gender, enrollment_year, bio, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_profile(user_id: int, fields: dict) -> dict | None:
    _ensure()
    updates = {key: value for key, value in fields.items() if key in PROFILE_FIELDS}
    if updates:
        assignments = ", ".join(f"{key} = ?" for key in updates)
        conn = get_conn()
        try:
            conn.execute(
                f"UPDATE users SET {assignments} WHERE id = ?",
                (*[str(value) for value in updates.values()], user_id),
            )
            conn.commit()
        finally:
            conn.close()
    return get_profile(user_id)


def set_password(user_id: int, password_hash: str) -> None:
    _ensure()
    conn = get_conn()
    try:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        conn.commit()
    finally:
        conn.close()


def get_password_hash(user_id: int) -> str | None:
    _ensure()
    conn = get_conn()
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["password_hash"] if row else None
    finally:
        conn.close()
