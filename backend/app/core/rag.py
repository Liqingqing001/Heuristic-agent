"""课程 RAG：共享分块、BM25 + 向量召回、RRF 融合与可恢复降级。

词法模式不加载任何模型。向量索引按代发布；只接受仍存在于当前知识库、
内容哈希一致的片段，避免修改或删除文件后继续引用旧内容。
"""
from __future__ import annotations

import logging
import os
import threading
import time

os.environ.setdefault('ANONYMIZED_TELEMETRY', 'False')
import numpy as _np
if not hasattr(_np, 'float_'):
    _np.float_ = _np.float64
import chromadb

from app import config
from app.core import corpus, embedding, rag_index
from app.core.retrieval import lexical_rank, rrf, select_diverse

logger = logging.getLogger(__name__)
KP_COLLECTION = 'kp_points'
COLLECTIONS = list(rag_index.COLLECTIONS)
split_markdown = corpus.split_markdown
_client = None
_client_path = None
_client_lock = threading.Lock()
_health_lock = threading.Lock()
_retry_after = 0.0
_vector_error = None
_last_mode = 'not_used'


def get_db():
    global _client, _client_path
    path = str(config.VECTOR_DB_DIR)
    with _client_lock:
        if _client is None or _client_path != path:
            _client = chromadb.PersistentClient(path=path)
            _client_path = path
        return _client


def reset_retrieval() -> dict:
    """教师可手动解除重试冷却；不会下载模型或修改向量数据。"""
    global _retry_after, _vector_error
    with _health_lock:
        _retry_after = 0.0
        _vector_error = None
    return retrieval_status()


def _failed(exc: Exception):
    global _retry_after, _vector_error
    with _health_lock:
        _retry_after = time.monotonic() + config.RAG_RETRY_SECONDS
        _vector_error = type(exc).__name__
    # 不记录原始查询、学生代码或潜在包含凭据的第三方错误正文。
    logger.warning('RAG 向量检索暂不可用，使用词法检索（%s）', type(exc).__name__)


def ingest() -> dict:
    snapshot = corpus.snapshot()
    result = rag_index.build(get_db(), config.VECTOR_DB_DIR, snapshot)
    reset_retrieval()
    return result


def _categories(categories):
    if categories is None:
        return set(COLLECTIONS)
    values = {KP_COLLECTION if c == 'kp' else c for c in categories}
    if not values.issubset(COLLECTIONS):
        raise ValueError('未知知识库分类')
    return values


def _vector_candidates(query, chunks, cats, limit):
    if time.monotonic() < _retry_after:
        return [], None
    manifest = rag_index.read_manifest(config.VECTOR_DB_DIR)
    if not manifest:
        return [], None
    # 同一查询只计算一次向量，四个知识分类共用。
    vector = embedding.embed_query(query)
    if manifest['model_signature'] != embedding.model_signature():
        raise ValueError('模型或向量后端已变化，需要重新建库')
    current = {c['chunk_id']: c for c in chunks}
    db = get_db()
    candidates = []
    for category in sorted(cats):
        coll = db.get_collection(name=manifest['collections'][category])
        count = coll.count()
        if not count:
            continue
        data = coll.query(query_embeddings=[vector], n_results=min(limit, count), include=['metadatas', 'distances'])
        for chunk_id, meta, distance in zip(data['ids'][0], data['metadatas'][0], data['distances'][0]):
            chunk = current.get(chunk_id)
            if not chunk or not meta or meta.get('content_hash') != chunk['content_hash']:
                continue
            if distance is None or not _np.isfinite(distance) or distance > config.RAG_MAX_DISTANCE:
                continue
            candidates.append({**chunk, 'vector_distance': float(distance)})
    candidates.sort(key=lambda item: item['vector_distance'])
    return candidates[:limit], manifest


def search(query: str, categories: list[str] | None = None, top_k: int = config.TOP_K,
           *, mode: str = 'hybrid', audience: str = 'hint', quotas: dict | None = None) -> list[dict]:
    """候选召回 -> RRF -> 文档多样性。distance 为融合排名兼容字段，非余弦距离。

    audience='hint' 默认排除完整题解。离线评测可显式选择 audience='all'。
    """
    global _last_mode, _vector_error, _retry_after
    if mode not in ('lexical', 'hybrid') or audience not in ('hint', 'all'):
        raise ValueError('不支持的检索模式或内容层级')
    cats = _categories(categories)
    query = query.strip()
    if top_k <= 0 or not query or not cats:
        return []
    top_k = min(top_k, 100)
    snapshot = corpus.snapshot()
    normalized = {'kp' if c == KP_COLLECTION else c for c in cats}
    chunks = [c for c in snapshot.chunks if c['category'] in normalized and (audience == 'all' or c.get('audience', 'hint') == 'hint')]
    limit = max(20, top_k * 4)
    lexical = lexical_rank(query, chunks, limit=limit)
    vectors, manifest = [], None
    if mode == 'hybrid' and chunks:
        try:
            vectors, manifest = _vector_candidates(query, chunks, cats, limit)
            if manifest and time.monotonic() >= _retry_after:
                with _health_lock:
                    _vector_error = None
                    _retry_after = 0.0
        except Exception as exc:
            _failed(exc)
    used = 'hybrid' if vectors else 'lexical'
    _last_mode = used
    fused = rrf([lexical, vectors], limit=limit)
    selected = select_diverse(fused, top_k=top_k, per_document=2, quotas=quotas)
    return [{**item, 'search_mode': used,
             'index_version': manifest['source_version'] if manifest and 'vector_distance' in item else snapshot.version,
             'source_version': snapshot.version} for item in selected]


def _local_chunks() -> list[dict]:
    return list(corpus.snapshot().chunks)


def _lexical_search(query, cats, top_k):
    return search(query, categories=cats, top_k=top_k, mode='lexical')


def stats() -> dict:
    """保留原四分类计数响应；统计不加载 embedding，也不隐式建库。"""
    manifest = rag_index.read_manifest(config.VECTOR_DB_DIR)
    return dict(manifest['counts']) if manifest else {c: 0 for c in COLLECTIONS}


def retrieval_status() -> dict:
    try:
        manifest = rag_index.read_manifest(config.VECTOR_DB_DIR)
        snapshot = corpus.snapshot()
        state = 'missing' if not manifest else 'stale' if manifest['source_version'] != snapshot.version or manifest.get('model_name', config.EMBEDDING_MODEL) != config.EMBEDDING_MODEL else 'ready'
    except Exception:
        manifest, state = None, 'error'
    return {
        'last_mode': _last_mode, 'index_state': state,
        'index_version': manifest['source_version'] if manifest else None,
        'built_at': manifest.get('built_at') if manifest else None,
        'embedding_backend': embedding.backend(), 'vector_error': _vector_error,
        'retry_in_seconds': max(0, round(_retry_after - time.monotonic())),
        'rebuild_required': state != 'ready',
    }
