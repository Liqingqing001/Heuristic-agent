"""本地 BGE 向量化模型（懒加载单例，首次调用会下载模型）。"""
from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL

_model: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """文本 -> 归一化向量（归一化后可用点积近似余弦相似度）。"""
    model = get_embedder()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
