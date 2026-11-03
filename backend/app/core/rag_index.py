"""按代构建向量索引；完整写入后用原子 manifest 切换四个 collection。

旧代保留，构建失败不修改活动 manifest。单进程内建库串行，读取使用一份
manifest 快照。不同进程同时建库不受支持；部署请使用单个建库 worker。
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core import embedding

FORMAT_VERSION = 1
BUILD_LOCK = threading.Lock()
COLLECTIONS = ('lecture', 'solutions', 'buglib', 'kp_points')


def read_manifest(root: Path) -> dict | None:
    path = root / 'active-index.json'
    if not path.exists():
        return None
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('format') != FORMAT_VERSION or set(manifest.get('collections', {})) != set(COLLECTIONS):
        raise ValueError('不支持的 RAG 索引清单，请重新建库')
    required = ('source_version', 'model_signature', 'counts')
    if any(key not in manifest for key in required) or set(manifest['counts']) != set(COLLECTIONS):
        raise ValueError('RAG 索引清单不完整，请重新建库')
    return manifest


def _metadata(chunk: dict) -> dict:
    return {k: v for k, v in chunk.items() if k != 'text' and isinstance(v, (str, int, float, bool))}


def build(db, root: Path, snapshot) -> dict:
    with BUILD_LOCK:
        signature = embedding.model_signature()
        try:
            old = read_manifest(root)
        except (ValueError, KeyError, TypeError):
            # 损坏的清单不能用来复用向量，但教师仍可重新建库自愈。
            old = None
        if old and old['source_version'] == snapshot.version and old['model_signature'] == signature:
            return dict(old['counts'])
        # 只复用同一模型、后端和预处理版本的归一化向量。
        reusable = {}
        if old and old['model_signature'] == signature:
            for name in old['collections'].values():
                coll = db.get_collection(name=name)
                records = coll.get(include=['embeddings', 'metadatas'])
                vectors = records['embeddings']
                if vectors is not None:
                    for meta, vector in zip(records['metadatas'], vectors):
                        reusable[meta['content_hash']] = list(vector)
        generation = uuid.uuid4().hex[:16]
        names, counts, created = {}, {}, []
        root.mkdir(parents=True, exist_ok=True)
        staging = root / f'.active-index-{generation}.tmp'
        try:
            for category in COLLECTIONS:
                name = f'rag_{generation}_{category}'
                coll = db.create_collection(name=name, metadata={'hnsw:space': 'cosine'})
                created.append(name)
                names[category] = name
                normalized = 'kp' if category == 'kp_points' else category
                chunks = [c for c in snapshot.chunks if c['category'] == normalized]
                # 限制 embedding 与 Chroma 批大小，避免一次吞下整个课程。
                for start in range(0, len(chunks), 64):
                    batch = chunks[start:start + 64]
                    missing = list({c['content_hash']: c['text'] for c in batch if c['content_hash'] not in reusable}.items())
                    if missing:
                        vectors = embedding.embed_texts([text for _, text in missing])
                        if len(vectors) != len(missing):
                            raise ValueError('向量数量与文档不一致')
                        reusable.update((key, vector) for (key, _), vector in zip(missing, vectors))
                    coll.upsert(
                        ids=[c['chunk_id'] for c in batch], documents=[c['text'] for c in batch],
                        metadatas=[_metadata(c) for c in batch],
                        embeddings=[reusable[c['content_hash']] for c in batch],
                    )
                counts[category] = coll.count()
                if counts[category] != len(chunks):
                    raise ValueError('索引条目校验失败')
            manifest = {
                'format': FORMAT_VERSION, 'generation': generation,
                'source_version': snapshot.version, 'model_signature': signature,
                'model_name': embedding.EMBEDDING_MODEL,
                'collections': names, 'counts': counts,
                'files': snapshot.files,
                'built_at': datetime.now(timezone.utc).isoformat(),
            }
            with staging.open('w', encoding='utf-8') as handle:
                json.dump(manifest, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staging, root / 'active-index.json')
        except BaseException:
            staging.unlink(missing_ok=True)
            for name in created:
                try:
                    db.delete_collection(name=name)
                except Exception:
                    pass
            raise
        return counts
