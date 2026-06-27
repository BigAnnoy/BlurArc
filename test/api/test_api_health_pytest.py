"""
API 健康检查测试 (pytest版本)
测试 /api/health 端点是否正常工作
"""

import json
from datetime import datetime


def test_health_check(client):
    """测试健康检查端点是否正常响应"""
    response = client.get('/api/health')
    
    assert response.status_code == 200
    
    data = json.loads(response.data)
    
    assert 'status' in data
    assert 'timestamp' in data
    assert data['status'] == 'ok'
    
    try:
        datetime.fromisoformat(data['timestamp'])
    except ValueError:
        assert False, 'timestamp 格式不正确'


def test_health_check_content_type(client):
    """测试健康检查端点返回正确的 Content-Type"""
    response = client.get('/api/health')
    
    assert response.content_type == 'application/json'


def test_health_check_cors_headers(client):
    """测试健康检查端点返回正确的 CORS 头"""
    response = client.get('/api/health')
    
    assert 'Access-Control-Allow-Origin' in response.headers
    assert len(response.headers['Access-Control-Allow-Origin']) > 0
