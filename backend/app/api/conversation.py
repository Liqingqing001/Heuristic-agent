"""会话管理接口：创建 / 列表 / 查消息 / 删除。"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core import store

router = APIRouter(prefix="/api", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    title: str = "新会话"


@router.post("/conversations")
def create_conversation(req: CreateConversationRequest):
    return store.create_conversation(req.title)


@router.get("/conversations")
def list_conversations():
    return store.list_conversations()


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: int):
    return store.get_messages(conversation_id)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int):
    store.delete_conversation(conversation_id)
    return {"status": "ok"}
