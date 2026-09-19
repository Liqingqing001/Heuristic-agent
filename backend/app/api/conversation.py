"""会话管理接口：创建 / 列表 / 查消息 / 删除。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core import store
from app.core.auth import get_current_user

router = APIRouter(prefix="/api", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    title: str = "新会话"


@router.post("/conversations")
def create_conversation(req: CreateConversationRequest, user: dict = Depends(get_current_user)):
    return store.create_conversation(user["user_id"], req.title)


@router.get("/conversations")
def list_conversations(user: dict = Depends(get_current_user)):
    return store.list_conversations(user["user_id"])


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: int, user: dict = Depends(get_current_user)):
    if not store.belongs_to_user(conversation_id, user["user_id"]):
        raise HTTPException(403, "无权访问该会话")
    return store.get_messages(conversation_id)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, user: dict = Depends(get_current_user)):
    store.delete_conversation(conversation_id, user["user_id"])
    return {"status": "ok"}