"""知识库参数边界与目录遍历回归。"""
import pytest


@pytest.mark.parametrize('category', ['../', '../solutions', '../../', '/tmp', 'unknown'])
def test_invalid_category(client, category):
    response = client.get('/api/knowledge/list', params={'category': category})
    assert response.status_code == 422


@pytest.mark.parametrize('category', ['lecture', 'solutions', 'buglib', 'kp'])
def test_valid_category(client, category):
    response = client.get('/api/knowledge/list', params={'category': category})
    assert response.status_code == 200
    assert response.json()['total'] > 0


@pytest.mark.parametrize('limit', [-1, 0, 101])
def test_invalid_search_limit(client, limit):
    assert client.get('/api/knowledge/search', params={'q': '链表', 'top_k': limit}).status_code == 422


def test_search_limit(client):
    data = client.get('/api/knowledge/search', params={'q': '链表', 'top_k': 1}).json()
    assert data['total'] == len(data['items']) == 1
