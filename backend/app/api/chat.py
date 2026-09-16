"""苏格拉底对话接口（SSE 流式 + 会话持久化）。"""
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.socratic import answer_stream
from app.core import store

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    conversation_id: int | None = None


def _sse(payload) -> str:
    # 用 JSON 编码避免 token 内的换行破坏 SSE 帧
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream(question: str, conversation_id: int | None):
    try:
        # 无会话时自动新建
        if conversation_id is None:
            conversation_id = store.create_conversation()["id"]

        # 从数据库加载历史（不含当前这条），作为 LLM 的上下文
        history = store.get_messages(conversation_id)

        # 先落库用户消息，并自动为"新会话"命名
        store.add_message(conversation_id, "user", question)
        store.maybe_update_title(conversation_id, question)

        # 流式生成，累积完整回复后落库
        full_reply = ""
        for token in answer_stream(question, history):
            full_reply += token
            yield _sse({"token": token})

        store.add_message(conversation_id, "assistant", full_reply)
        yield _sse({"conversation_id": conversation_id, "done": True})
    except Exception as e:  # 未配置 key、网络失败等
        yield _sse({"error": str(e)})
        yield _sse({"done": True})


@router.post("/chat")
def chat_endpoint(req: ChatRequest):
    return StreamingResponse(
        _stream(req.question, req.conversation_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
