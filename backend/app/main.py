"""FastAPI 应用入口。"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, chat, classes, code, conversation, knowledge, llm, profile
from app.config import FRONTEND_DIST
from app.core.db import init_db

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    result = init_db()
    logger.info("数据库就绪：%s", result)
    yield


app = FastAPI(
    title="智育助教 Agent",
    description="基于 RAG 与苏格拉底教学法的数据结构智能助教",
    lifespan=lifespan,
)

# 开发阶段允许跨域，方便 vite dev server 直连后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(code.router)
app.include_router(knowledge.router)
app.include_router(conversation.router)
app.include_router(classes.router)
app.include_router(llm.router)
app.include_router(profile.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 生产环境：若前端已 build，则由 FastAPI 直接托管静态产物
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
