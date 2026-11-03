"""全局配置：读取 .env，定义路径常量。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/ 目录
BASE_DIR = Path(__file__).resolve().parent.parent
# 加载 .env（override=True：.env 优先级高于系统环境变量，改 .env 即可生效）
load_dotenv(BASE_DIR / ".env", override=True)
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", str(DATA_DIR / "knowledge")))
VECTOR_DB_DIR = Path(os.getenv("VECTOR_DB_DIR", str(DATA_DIR / "vector_db")))


# DeepSeek 大模型
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 是否允许回退到服务端 .env 里的公共 key。
# 默认关闭：强制 BYOK，没填个人 key 的请求直接报错，不会消耗部署者的额度。
ALLOW_SERVER_KEY = os.getenv("ALLOW_SERVER_KEY", "0").strip().lower() in ("1", "true", "yes", "on")

# 本地向量化模型
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

# 检索相关知识点数量
TOP_K = int(os.getenv("TOP_K", "3"))

# 前端构建产物目录（用于生产环境静态托管，开发时用 vite dev server）
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

# RAG：余弦距离上限需结合本课程评测校准，越小越保守。
RAG_MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", "0.45"))
RAG_RETRY_SECONDS = int(os.getenv("RAG_RETRY_SECONDS", "60"))
