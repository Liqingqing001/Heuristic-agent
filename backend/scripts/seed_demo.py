"""生成演示数据：8 个学生 + 多次提交 + 批阅 + 知识点掌握度。

用法（在 backend 目录下）：

    py scripts\\seed_demo.py

幂等：重复运行不会重复建用户/任务，提交会被覆盖为同一份样例。
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core import store  # noqa: E402
from app.core.auth import hash_password  # noqa: E402
from app.core.db import get_conn, init_db  # noqa: E402

PASSWORD = "demo123456"

STUDENTS = [
    ("demo_stu01", "张伟"),
    ("demo_stu02", "李娜"),
    ("demo_stu03", "王强"),
    ("demo_stu04", "刘洋"),
    ("demo_stu05", "陈静"),
    ("demo_stu06", "赵磊"),
    ("demo_stu07", "孙悦"),
    ("demo_stu08", "周涛"),
]

ASSIGNMENTS = [
    {
        "title": "单链表插入训练",
        "description": "在结点 p 之后插入新结点 q，检查插入后链表是否完整。",
        "type": "code",
        "kp_ids": ["ds-01-02"],
        "due_at": "2026-12-01T23:59",
    },
    {
        "title": "单链表反转与快慢指针",
        "description": "实现单链表反转，并判断链表中是否有环。",
        "type": "code",
        "kp_ids": ["ds-01-03"],
        "due_at": "2026-12-08T23:59",
    },
    {
        "title": "栈与队列的区别",
        "description": "用自己的话说明栈和队列的插入删除位置差异，各举一个应用场景。",
        "type": "question",
        "kp_ids": ["ds-02-01"],
        "due_at": "2026-12-05T23:59",
    },
    {
        "title": "括号匹配与表达式求值",
        "description": "用栈判断括号序列是否合法，并说明遇到不匹配时怎么定位。",
        "type": "code",
        "kp_ids": ["ds-02-03"],
        "due_at": "2026-12-12T23:59",
    },
]

ERROR_SETS = [
    ["断链"],
    ["指针顺序错误", "断链"],
    ["内存泄漏"],
    ["循环边界"],
    ["空指针"],
    ["递归基线缺失"],
    ["悬空指针"],
    ["其他"],
]

SEVERITIES = ["low", "medium", "high"]

FEEDBACKS = [
    "指针顺序已经改对，但删除时仍然没有释放内存，注意 new/free 要成对出现。",
    "思路对了，建议先画一遍插入前后的指针图，再检查边界情况。",
    "边界处理还差一点：空表和表尾两种情况都要单独考虑。",
    "这次进步明显，反转的三指针写法已经正确，继续练快慢指针。",
    "判空条件写反了，空表时会直接解引用空指针，对照讲义再改一版。",
]

CODE_SAMPLES = [
    """void insertAfter(Node* p, Node* q) {
    p->next = q;
    q->next = p->next;
}""",
    """void removeAfter(Node* p) {
    Node* t = p->next;
    p->next = t->next;
}""",
    """int count(Node* head) {
    int n = 0;
    while (head->next != NULL) { n++; head = head->next; }
    return n;
}""",
    """void reverse(Node* head) {
    Node* cur = head;
    while (cur != NULL) {
        Node* nxt = cur->next;
        cur->next = cur;
        cur = nxt;
    }
}""",
]

AI_TEMPLATES = [
    "先定位问题：插入时先改了 `p->next`，原来的后继地址就丢了，后面再读 `p->next` 拿到的是新结点自己。\n\n反问你一句：执行完第一条赋值后，`q->next` 应该指向谁？",
    "这段删除只把结点从链上摘下来了，但没有释放内存，被摘下来的结点再也没有指针指向它。\n\n想一想：那个结点的内存最后由谁归还？",
    "循环条件用的是 `head->next`，最后一个结点会被漏掉；链表为空时还会直接解引用空指针。\n\n如果 `head` 是 NULL，这个循环条件会先发生什么？",
    "反转时把 `cur->next` 指向了 `cur` 自己，链表立刻变成自环。\n\n先想清楚：反转过程中你需要同时记住几个指针？它们分别指向谁？",
]


def ensure_students() -> list[dict]:
    conn = get_conn()
    created = 0
    try:
        for username, display in STUDENTS:
            row = conn.execute("SELECT id, username, display_name FROM users WHERE username = ?", (username,)).fetchone()
            if row:
                continue
            conn.execute(
                "INSERT INTO users (username, password_hash, role, display_name) VALUES (?, ?, 'student', ?)",
                (username, hash_password(PASSWORD), display),
            )
            created += 1
        conn.commit()
        rows = conn.execute(
            f"SELECT id, username, display_name FROM users WHERE username IN ({','.join('?' * len(STUDENTS))}) ORDER BY username",
            [item[0] for item in STUDENTS],
        ).fetchall()
    finally:
        conn.close()
    print(f"学生：新建 {created} 个，现有 {len(rows)} 个")
    return [dict(row) for row in rows]


def ensure_assignments(class_id: int, teacher_id: int) -> list[dict]:
    existing = {item["title"]: item for item in store.list_assignments(class_id)}
    for spec in ASSIGNMENTS:
        if spec["title"] in existing:
            continue
        store.create_assignment(
            class_id=class_id,
            title=spec["title"],
            description=spec["description"],
            type_=spec["type"],
            kp_ids=spec["kp_ids"],
            due_at=spec["due_at"],
            created_by=teacher_id,
        )
    return store.list_assignments(class_id)


def main() -> int:
    init_db()
    teacher = None
    students = ensure_students()
    conn = get_conn()
    try:
        teacher = conn.execute(
            "SELECT id, username FROM users WHERE username = 'demo_teacher'"
        ).fetchone()
    finally:
        conn.close()
    if not teacher:
        print("找不到 demo_teacher，请先运行一次应用或创建演示教师")
        return 1

    classes = store.list_classes_taught(teacher["id"])
    if not classes:
        print("demo_teacher 还没有班级")
        return 1
    cls = classes[0]
    print("班级：", cls["name"], "邀请码", cls["code"])

    for student in students:
        store.join_class(cls["code"], student["id"])

    assignments = {item["title"]: item for item in ensure_assignments(cls["id"], teacher["id"])}
    print("任务：", list(assignments))

    code_titles = ["单链表插入训练", "单链表反转与快慢指针", "括号匹配与表达式求值"]
    submitted = 0
    graded = 0
    for index, student in enumerate(students):
        # 前 6 个学生交两次，后 2 个只交第一次
        limit = 2 if index < 6 else 1
        for slot, title in enumerate(code_titles[:limit]):
            assignment = assignments.get(title)
            if not assignment:
                continue
            error_types = ERROR_SETS[(index + slot) % len(ERROR_SETS)]
            severity = SEVERITIES[(index + slot) % len(SEVERITIES)]
            hint = 1 + (index + slot) % 3
            diagnosis = {
                "error_types": error_types,
                "kp_ids": assignment["kp_ids"][:1],
                "severity": severity,
                "hint_level_reached": hint,
                "next_question": "如果把边界情况单独拿出来，你会先检查哪个指针？",
                "source": "model",
            }
            code = CODE_SAMPLES[(index + slot) % len(CODE_SAMPLES)]
            ai_text = AI_TEMPLATES[(index + slot) % len(AI_TEMPLATES)]
            store.upsert_submission(
                assignment_id=assignment["id"],
                user_id=student["id"],
                content=code,
                language="cpp",
                status="analyzed",
                ai_result=ai_text,
                diagnosis=diagnosis,
            )
            submitted += 1
            store.record_mastery(student["id"], diagnosis["kp_ids"], hint, severity)

            # 约 2/3 的提交已经批阅，留一部分待批阅
            if (index + slot) % 3 != 1:
                score = 55 + ((index * 7 + slot * 11) % 41)
                conn = get_conn()
                try:
                    row = conn.execute(
                        "SELECT id FROM submissions WHERE assignment_id = ? AND user_id = ?",
                        (assignment["id"], student["id"]),
                    ).fetchone()
                finally:
                    conn.close()
                if row:
                    store.grade_submission(
                        submission_id=row["id"],
                        teacher_id=teacher["id"],
                        score=score,
                        feedback=FEEDBACKS[(index + slot) % len(FEEDBACKS)],
                    )
                    graded += 1

        # 问答任务：前 5 个学生提交
        if index < 5:
            assignment = assignments.get("栈与队列的区别")
            if assignment:
                store.upsert_submission(
                    assignment_id=assignment["id"],
                    user_id=student["id"],
                    content="栈只在一端插入和删除，后进先出；队列一端进另一端出，先进先出。栈用于函数调用和括号匹配，队列用于任务调度。",
                    language="text",
                    status="submitted",
                    ai_result="",
                    diagnosis={},
                )
                submitted += 1

    print(f"提交：{submitted} 条，其中已批阅 {graded} 条")
    print("完成。用 demo_teacher / demo123456 登录看教师端，用 demo_student / demo123456 看学生端。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
