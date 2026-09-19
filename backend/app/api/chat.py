"""苏格拉底对话接口（SSE 流式 + 会话持久化）。"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.socratic import answer_stream
from app.core import store
from app.core.auth import get_current_user

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    conversation_id: int | None = None


def _sse(payload) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream(question: str, conversation_id: int | None, user_id: int):
    try:
        # 无会话时自动新建
        if conversation_id is None:
            conversation_id = store.create_conversation(user_id)["id"]
        elif not store.belongs_to_user(conversation_id, user_id):
            # 会话不属于当前用户 → 重开一个
            conversation_id = store.create_conversation(user_id)["id"]

        history = store.get_messages(conversation_id)

        store.add_message(conversation_id, "user", question)
        store.maybe_update_title(conversation_id, question)

        full_reply = ""
        for token in answer_stream(question, history):
            full_reply += token
            yield _sse({"token": token})

        store.add_message(conversation_id, "assistant", full_reply)
        yield _sse({"conversation_id": conversation_id, "done": True})
    except Exception as e:
        yield _sse({"error": str(e)})
        yield _sse({"done": True})


@router.post("/chat")
def chat_endpoint(req: ChatRequest, user: dict = Depends(get_current_user)):
    return StreamingResponse(
        _stream(req.question, req.conversation_id, user["user_id"]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )