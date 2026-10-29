"""文本向量化：优先 ONNX（fastembed），不可用时回退 sentence-transformers。

用 ONNX 的原因：
- 不依赖 torch（torch 约 2GB，且在部分 Windows 机器上会被应用控制策略拦截）；
- 模型体积约 90MB，小服务器/ARM 也能跑；
- 输出与 BGE 原模型一致（512 维），和已有向量库兼容。
"""
from __future__ import annotations

from app.config import DATA_DIR, EMBEDDING_MODEL

_model = None
_backend: str | None = None


def _load():
    global _model, _backend
    if _model is not None:
        return _model

    try:
        from fastembed import TextEmbedding

        _model = TextEmbedding(
            model_name=EMBEDDING_MODEL,
            cache_dir=str(DATA_DIR / "model_cache"),
        )
        _backend = "onnx"
        return _model
    except Exception as exc:  # 没装 fastembed / 模型下载失败 → 尝试 torch
        print(f"[embedding] ONNX 向量模型不可用，回退 sentence-transformers：{exc}")

    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer(EMBEDDING_MODEL)
    _backend = "torch"
    return _model


def get_embedder():
    return _load()


def backend() -> str | None:
    """当前后端：'onnx' / 'torch' / None（还没加载）。"""
    return _backend


def embed_texts(texts: list[str]) -> list[list[float]]:
    """文本 -> 归一化向量（归一化后可用点积近似余弦相似度）。"""
    model = _load()
    if _backend == "onnx":
        import numpy as np

        vectors = np.asarray(list(model.embed(texts)), dtype="float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / np.clip(norms, 1e-12, None)
        return vectors.tolist()
    return model.encode(texts, normalize_embeddings=True).tolist()
