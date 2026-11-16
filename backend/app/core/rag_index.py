"""按代构建向量索引（numpy 暴力检索），完整写入后用原子 manifest 切换。

不依赖 chromadb / hnswlib 等原生扩展：一代索引就是一个目录，内含
``vectors.npy``（float32，已归一化的行向量矩阵）与 ``chunks.json``
（与矩阵行序一一对应的片段元数据）。课程语料只有几十到几百个分块，
暴力余弦检索是微秒级，没有必要引入近似最近邻索引。

旧代保留一代用于复用向量；构建失败不修改活动 manifest。读取方只认
manifest 指向的目录，因此旧格式（chromadb 目录）不会被误读。
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.core import embedding

FORMAT_VERSION = 2
BUILD_LOCK = threading.Lock()
COLLECTIONS = ('lecture', 'solutions', 'buglib', 'kp_points')
VECTORS_FILE = 'vectors.npy'
CHUNKS_FILE = 'chunks.json'

_load_lock = threading.Lock()
_load_cache: dict = {}


def read_manifest(root: Path) -> dict | None:
    path = root / 'active-index.json'
    if not path.exists():
        return None
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('format') != FORMAT_VERSION or set(manifest.get('collections', {})) != set(COLLECTIONS):
        raise ValueError('不支持的 RAG 索引清单，请重新建库')
    required = ('source_version', 'model_signature', 'counts', 'dir')
    if any(key not in manifest for key in required) or set(manifest['counts']) != set(COLLECTIONS):
        raise ValueError('RAG 索引清单不完整，请重新建库')
    return manifest


def load_generation(root: Path, manifest: dict) -> tuple[np.ndarray, list[dict]]:
    """读取活动代的向量矩阵与元数据；同一代在进程内缓存一份。"""
    directory = Path(root) / str(manifest['dir'])
    vectors_path = directory / VECTORS_FILE
    chunks_path = directory / CHUNKS_FILE
    if not vectors_path.exists() or not chunks_path.exists():
        raise ValueError('索引文件缺失，请重新建库')
    key = (str(vectors_path), vectors_path.stat().st_mtime_ns, chunks_path.stat().st_mtime_ns)
    with _load_lock:
        cached = _load_cache.get('active')
        if cached and cached[0] == key:
            return cached[1], cached[2]
    matrix = np.load(vectors_path)
    chunks = json.loads(chunks_path.read_text(encoding='utf-8'))
    if matrix.ndim != 2 or matrix.shape[0] != len(chunks):
        raise ValueError('索引矩阵与片段元数据不一致，请重新建库')
    with _load_lock:
        _load_cache['active'] = (key, matrix, chunks)
    return matrix, chunks


def _metadata(chunk: dict) -> dict:
    return {k: v for k, v in chunk.items() if k != 'text' and isinstance(v, (str, int, float, bool))}


def _reusable_vectors(root: Path, old: dict | None, signature: str) -> dict:
    """同模型、同后端、同预处理版本的向量可直接复用。"""
    if not old or old.get('model_signature') != signature:
        return {}
    try:
        matrix, chunks = load_generation(root, old)
    except (ValueError, OSError, json.JSONDecodeError):
        return {}
    return {meta['content_hash']: matrix[index] for index, meta in enumerate(chunks)}


def _prune(root: Path, keep: set[str]) -> None:
    for path in root.glob('gen-*'):
        if path.is_dir() and path.name not in keep:
            shutil.rmtree(path, ignore_errors=True)


def build(root: Path, snapshot) -> dict:
    root = Path(root)
    with BUILD_LOCK:
        signature = embedding.model_signature()
        try:
            old = read_manifest(root)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            # 损坏的清单不能用来复用向量，但教师仍可重新建库自愈。
            old = None
        if old and old['source_version'] == snapshot.version and old['model_signature'] == signature:
            return dict(old['counts'])

        reusable = _reusable_vectors(root, old, signature)
        generation = uuid.uuid4().hex[:16]
        dirname = f'gen-{generation}'
        root.mkdir(parents=True, exist_ok=True)
        staging = root / f'.{dirname}.tmp'
        final = root / dirname
        try:
            rows, metas, counts = [], [], {}
            for category in COLLECTIONS:
                normalized = 'kp' if category == 'kp_points' else category
                chunks = [c for c in snapshot.chunks if c['category'] == normalized]
                # 限制 embedding 批大小，避免一次吞下整门课程。
                for start in range(0, len(chunks), 64):
                    batch = chunks[start:start + 64]
                    missing = list({c['content_hash']: c['text'] for c in batch
                                    if c['content_hash'] not in reusable}.items())
                    if missing:
                        vectors = embedding.embed_texts([text for _, text in missing])
                        if len(vectors) != len(missing):
                            raise ValueError('向量数量与文档不一致')
                        reusable.update((key, vector) for (key, _), vector in zip(missing, vectors))
                    for chunk in batch:
                        rows.append(reusable[chunk['content_hash']])
                        metas.append(_metadata(chunk))
                counts[category] = len(chunks)

            matrix = np.zeros((0, 0), dtype='float32') if not rows else np.asarray(rows, dtype='float32')
            if len(rows):
                if matrix.ndim != 2 or matrix.shape[0] != len(metas):
                    raise ValueError('索引条目校验失败')
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                matrix = matrix / np.clip(norms, 1e-12, None)
            elif len(metas) != 0:
                raise ValueError('索引条目校验失败')

            staging.mkdir(parents=True, exist_ok=True)
            np.save(staging / VECTORS_FILE, matrix)
            (staging / CHUNKS_FILE).write_text(
                json.dumps(metas, ensure_ascii=False), encoding='utf-8')
            os.replace(staging, final)

            manifest = {
                'format': FORMAT_VERSION, 'generation': generation, 'dir': dirname,
                'source_version': snapshot.version, 'model_signature': signature,
                'model_name': embedding.EMBEDDING_MODEL,
                'collections': {c: f'rag_{generation}_{c}' for c in COLLECTIONS},
                'counts': counts, 'dim': int(matrix.shape[1]),
                'files': snapshot.files,
                'built_at': datetime.now(timezone.utc).isoformat(),
            }
            temp_manifest = root / f'.active-index-{generation}.tmp'
            with temp_manifest.open('w', encoding='utf-8') as handle:
                json.dump(manifest, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_manifest, root / 'active-index.json')
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            if final.exists() and not (root / 'active-index.json').exists():
                shutil.rmtree(final, ignore_errors=True)
            raise

        # 只保留当前代与上一代（上一代用于下次复用向量）。
        keep = {dirname}
        if old and old.get('dir'):
            keep.add(str(old['dir']))
        _prune(root, keep)
        return counts
