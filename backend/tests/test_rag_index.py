"""真实临时 Chroma + 假向量，测试索引事务，不下载模型。"""
import json
import pytest
from app import config
from app.core import embedding, rag

@pytest.fixture
def index_env(tmp_path, monkeypatch):
    knowledge = tmp_path / 'knowledge'
    (knowledge / 'lecture').mkdir(parents=True)
    (knowledge / 'lecture' / '链表.md').write_text('# 单链表\n\n## 插入\n先保存后继指针再插入结点。', encoding='utf-8')
    monkeypatch.setattr(config, 'KNOWLEDGE_DIR', knowledge)
    monkeypatch.setattr(config, 'VECTOR_DB_DIR', tmp_path / 'vectors')
    monkeypatch.setattr(embedding, 'model_signature', lambda: 'fake-3d-v1')
    batches = []
    def embed(texts):
        batches.extend(texts)
        return [[1., 0., 0.] for _ in texts]
    monkeypatch.setattr(embedding, 'embed_texts', embed)
    monkeypatch.setattr(embedding, 'embed_query', lambda query: [1., 0., 0.])
    rag.reset_retrieval()
    yield knowledge, batches
    rag.reset_retrieval()

def manifest():
    return json.loads((config.VECTOR_DB_DIR / 'active-index.json').read_text())

def test_incremental_reuses_vectors_and_removes_deleted_chunks(index_env):
    knowledge, embedded = index_env
    first = rag.ingest()
    before, initial = manifest(), len(embedded)
    assert first['lecture'] > 0
    assert rag.ingest() == first
    assert len(embedded) == initial
    assert manifest() == before
    (knowledge / 'lecture' / '队列.md').write_text('# 队列\n\n先进先出的队列。', encoding='utf-8')
    second = rag.ingest()
    assert 0 < len(embedded) - initial < second['lecture']
    (knowledge / 'lecture' / '链表.md').unlink()
    assert all(r['source'] != '链表.md' for r in rag.search('链表插入后继指针'))
    assert rag.ingest()['lecture'] < second['lecture']
    assert rag.retrieval_status()['index_state'] == 'ready'

def test_failed_build_keeps_active_generation(index_env, monkeypatch):
    knowledge, _ = index_env
    rag.ingest()
    before = manifest()
    names_before = {c.name for c in rag.get_db().list_collections()}
    (knowledge / 'lecture' / '队列.md').write_text('# 队列\n先进先出。', encoding='utf-8')
    def fail(texts): raise RuntimeError('simulated failure')
    monkeypatch.setattr(embedding, 'embed_texts', fail)
    with pytest.raises(RuntimeError): rag.ingest()
    assert manifest() == before
    assert {c.name for c in rag.get_db().list_collections()} == names_before
    assert rag.stats() == before['counts']
    assert rag.retrieval_status()['index_state'] == 'stale'

def test_modified_content_never_returns_stale_vector(index_env):
    knowledge, _ = index_env
    rag.ingest()
    (knowledge / 'lecture' / '链表.md').write_text('# 链表\n\n已修改为双向链表的前驱指针说明。', encoding='utf-8')
    result = rag.search('双向链表前驱指针')
    assert result and all('先保存后继' not in item['text'] for item in result)
    assert rag.retrieval_status()['index_state'] == 'stale'

def test_one_query_vector_and_recoverable_failure(index_env, monkeypatch):
    rag.ingest()
    queries = []
    def embed_query(query):
        queries.append(query)
        return [1., 0., 0.]
    monkeypatch.setattr(embedding, 'embed_query', embed_query)
    assert rag.search('单链表插入')
    assert len(queries) == 1
    def fail(query):
        queries.append(query)
        raise RuntimeError('offline')
    monkeypatch.setattr(embedding, 'embed_query', fail)
    assert all(r['retrieval'] == 'lexical' for r in rag.search('单链表插入'))
    count = len(queries)
    rag.search('单链表插入')
    assert len(queries) == count
    assert rag.retrieval_status()['retry_in_seconds'] > 0
    monkeypatch.setattr(embedding, 'embed_query', embed_query)
    rag.reset_retrieval()
    assert all(r['retrieval'] == 'hybrid' for r in rag.search('单链表插入'))

def test_missing_index_never_loads_model(index_env, monkeypatch):
    monkeypatch.setattr(embedding, 'embed_query', lambda _: pytest.fail('不应加载模型'))
    assert rag.search('链表插入')
    assert rag.search('今天纽约天气怎么样', mode='lexical') == []
    assert rag.retrieval_status()['index_state'] == 'missing'

def test_model_mismatch_degrades(index_env, monkeypatch):
    rag.ingest()
    monkeypatch.setattr(embedding, 'model_signature', lambda: 'other-model')
    assert all(r['retrieval'] == 'lexical' for r in rag.search('链表插入'))
    assert rag.retrieval_status()['vector_error'] == 'ValueError'

def test_reset_requires_teacher(client):
    assert client.post('/api/knowledge/retrieval/reset').status_code in (401, 403)
    assert 'index_state' in client.get('/api/knowledge/retrieval/status').json()


def test_corrupt_manifest_can_be_rebuilt(index_env):
    rag.ingest()
    (config.VECTOR_DB_DIR / 'active-index.json').write_text('{broken', encoding='utf-8')
    assert rag.search('链表插入')[0]['retrieval'] == 'lexical'
    assert rag.retrieval_status()['index_state'] == 'error'
    assert rag.ingest()['lecture'] > 0
    assert rag.retrieval_status()['index_state'] == 'ready'
