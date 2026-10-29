"""本地 BGE 向量化模型（懒加载单例，首次调用会下载模型）。

注意：sentence-transformers 依赖 torch，torch 的 DLL 在部分机器上会被
Windows 应用控制策略（Smart App Control / WDAC）拦截。这里把导入延迟到
真正建库/检索时，避免整个后端启动失败；调用方需自行处理不可用的情况。
"""
from __future__ import annotations

from app.config import EMBEDDING_MODEL

_model = None


def get_embedder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """文本 -> 归一化向量（归一化后可用点积近似余弦相似度）。"""
    model = get_embedder()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
