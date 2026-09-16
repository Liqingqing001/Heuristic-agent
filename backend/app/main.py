"""FastAPI 应用入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import chat, code, conversation, knowledge
from app.config import FRONTEND_DIST

app = FastAPI(title="智育助教 Agent", description="基于 RAG 与苏格拉底教学法的数据结构智能助教")

# 开发阶段允许跨域，方便 vite dev server 直连后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(code.router)
app.include_router(knowledge.router)
app.include_router(conversation.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 生产环境：若前端已 build，则由 FastAPI 直接托管静态产物
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
