"""接口冒烟测试：注册 → 建班 → 发任务 → 提交 → 批阅 → 看板 → 导出。"""
from __future__ import annotations

import uuid


def register(client, role: str, name: str | None = None):
    suffix = uuid.uuid4().hex[:6]
    username = name or f"{role}_{suffix}"
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "test123456", "role": role},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return data["token"], data


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_full_teaching_flow(client):
    teacher_token, teacher = register(client, "teacher", "t_flow")
    student_token, student = register(client, "student", "s_flow")

    # 学生不能建班
    assert client.post("/api/classes", json={"name": "x"}, headers=auth(student_token)).status_code == 403

    # 建班 + 加入
    response = client.post(
        "/api/classes", json={"name": "测试班", "term": "2026 春"}, headers=auth(teacher_token)
    )
    assert response.status_code == 200
    cls = response.json()
    assert len(cls["code"]) == 6

    response = client.post(
        "/api/classes/join", json={"code": cls["code"]}, headers=auth(student_token)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "joined"

    # 发任务
    response = client.post(
        f"/api/classes/{cls['id']}/assignments",
        json={
            "title": "单链表插入",
            "description": "检查指针顺序",
            "type": "code",
            "kp_ids": ["ds-01-02"],
            "due_at": "2030-01-01T00:00",
            "allow_late": True,
        },
        headers=auth(teacher_token),
    )
    assert response.status_code == 200
    assignment = response.json()
    assert assignment["allow_late"] == 1

    # 学生看到任务、未提交
    response = client.get(f"/api/classes/{cls['id']}/assignments", headers=auth(student_token))
    items = response.json()
    assert items and items[0]["my_submission"] is None
    assert items[0]["kp_titles"]["ds-01-02"]

    # 学生提交文字（code 类不允许走文字接口）
    assert client.post(
        f"/api/assignments/{assignment['id']}/submit",
        json={"content": "x"},
        headers=auth(student_token),
    ).status_code == 400

    # 改成问答类任务再提交
    response = client.patch(
        f"/api/assignments/{assignment['id']}",
        json={"type": "question"},
        headers=auth(teacher_token),
    )
    assert response.status_code == 200

    response = client.post(
        f"/api/assignments/{assignment['id']}/submit",
        json={"content": "栈是后进先出，队列是先进先出。"},
        headers=auth(student_token),
    )
    assert response.status_code == 200

    # 教师看提交并批阅
    response = client.get(
        f"/api/assignments/{assignment['id']}/submissions", headers=auth(teacher_token)
    )
    submissions = response.json()
    assert len(submissions) == 1
    submission_id = submissions[0]["id"]
    assert submissions[0]["status"] == "submitted"

    response = client.patch(
        f"/api/submissions/{submission_id}/grade",
        json={"score": 90, "feedback": "回答准确"},
        headers=auth(teacher_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "graded"

    # 学生能看到分数和评语
    response = client.get(f"/api/submissions/{submission_id}", headers=auth(student_token))
    assert response.json()["score"] == 90
    assert response.json()["feedback"] == "回答准确"

    # 看板
    response = client.get(f"/api/classes/{cls['id']}/overview", headers=auth(teacher_token))
    overview = response.json()
    assert overview["member_count"] == 1
    assert overview["assignment_count"] == 1
    assert overview["pending_grading"] == 0
    assert len(overview["score_distribution"]) == 5

    # 学生档案
    response = client.get(
        f"/api/classes/{cls['id']}/students/{student['user_id']}", headers=auth(teacher_token)
    )
    assert response.status_code == 200
    detail = response.json()
    assert len(detail["submissions"]) == 1
    assert detail["profile"]["username"] == student["username"]

    # 导出 CSV
    response = client.get(f"/api/classes/{cls['id']}/export.csv", headers=auth(teacher_token))
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "学号" in response.text
    assert "回答准确" in response.text

    # 越权：另一个老师看不到该班看板
    other_token, _ = register(client, "teacher", "t_other")
    assert client.get(
        f"/api/classes/{cls['id']}/overview", headers=auth(other_token)
    ).status_code == 403

    # 删除任务
    assert client.delete(
        f"/api/assignments/{assignment['id']}", headers=auth(teacher_token)
    ).status_code == 200
    assert client.get(
        f"/api/assignments/{assignment['id']}", headers=auth(teacher_token)
    ).status_code == 404


def test_closed_assignment_blocks_submission(client):
    teacher_token, _ = register(client, "teacher", "t_closed")
    student_token, _ = register(client, "student", "s_closed")

    response = client.post("/api/classes", json={"name": "截止测试班"}, headers=auth(teacher_token))
    cls = response.json()
    client.post("/api/classes/join", json={"code": cls["code"]}, headers=auth(student_token))

    response = client.post(
        f"/api/classes/{cls['id']}/assignments",
        json={
            "title": "已截止任务",
            "type": "question",
            "due_at": "2020-01-01T00:00",
            "allow_late": False,
        },
        headers=auth(teacher_token),
    )
    assignment = response.json()

    response = client.post(
        f"/api/assignments/{assignment['id']}/submit",
        json={"content": "迟交"},
        headers=auth(student_token),
    )
    assert response.status_code == 400
    assert "截止" in response.json()["detail"]


def test_delete_conversation_with_messages(client):
    """回归：早期 messages 表没有级联删除，删会话会 500。"""
    from app.core import store

    token, user = register(client, "student", "s_conv")
    conversation = store.create_conversation(user["user_id"], "测试会话")
    store.add_message(conversation["id"], "user", "你好")
    store.add_message(conversation["id"], "assistant", "你好，有什么问题？")

    response = client.delete(
        f"/api/conversations/{conversation['id']}", headers=auth(token)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # 会话和消息都没了
    response = client.get("/api/conversations", headers=auth(token))
    assert all(item["id"] != conversation["id"] for item in response.json())
    assert client.get(
        f"/api/conversations/{conversation['id']}/messages", headers=auth(token)
    ).status_code == 403


def test_profile_and_password(client):
    token, user = register(client, "student", "s_profile")
    response = client.patch(
        "/api/profile",
        json={"real_name": "测试同学", "school": "深圳技术大学"},
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["school"] == "深圳技术大学"

    response = client.post(
        "/api/profile/password",
        json={"old_password": "test123456", "new_password": "newpass123"},
        headers=auth(token),
    )
    assert response.status_code == 200

    assert client.post(
        "/api/auth/login",
        json={"username": user["username"], "password": "test123456"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"username": user["username"], "password": "newpass123"},
    ).status_code == 200
