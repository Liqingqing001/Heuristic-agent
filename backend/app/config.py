"""全局配置：读取 .env，定义路径常量。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/ 目录
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
VECTOR_DB_DIR = DATA_DIR / "vector_db"

# 加载 .env（override=True：.env 优先级高于系统环境变量，改 .env 即可生效）
load_dotenv(BASE_DIR / ".env", override=True)

# DeepSeek 大模型
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 本地向量化模型
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

# 检索相关知识点数量
TOP_K = int(os.getenv("TOP_K", "3"))

# 前端构建产物目录（用于生产环境静态托管，开发时用 vite dev server）
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
