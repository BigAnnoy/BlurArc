"""
API 健康检查测试
测试 /api/health 端点是否正常工作
"""

import sys
import json
from pathlib import Path
import unittest
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.api_server import app


class TestAPIHealth(unittest.TestCase):
    """API 健康检查测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建 Flask 测试客户端
        self.client = app.test_client()
        # 启用测试环境
        app.config['TESTING'] = True
    
    def test_health_check(self):
        """测试健康检查端点是否正常响应"""
        # 发送 GET 请求到健康检查端点
        response = self.client.get('/api/health')
        
        # 验证响应状态码为 200 OK
        self.assertEqual(response.status_code, 200)
        
        # 解析响应数据
        data = json.loads(response.data)
        
        # 验证响应数据包含预期的字段
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        
        # 验证 status 字段值为 'ok'
        self.assertEqual(data['status'], 'ok')
        
        # 验证 timestamp 字段格式正确
        try:
            datetime.fromisoformat(data['timestamp'])
        except ValueError:
            self.fail('timestamp 格式不正确')
    
    def test_health_check_content_type(self):
        """测试健康检查端点返回正确的 Content-Type"""
        response = self.client.get('/api/health')
        
        # 验证响应的 Content-Type 为 application/json
        self.assertEqual(response.content_type, 'application/json')
    
    def test_health_check_cors_headers(self):
        """测试健康检查端点返回正确的 CORS 头"""
        response = self.client.get('/api/health')
        
        # 验证响应包含 Access-Control-Allow-Origin 头
        self.assertIn('Access-Control-Allow-Origin', response.headers)
        # CORS 策略为白名单模式，响应应包含有效的 origin（测试环境为 localhost）
        self.assertTrue(len(response.headers['Access-Control-Allow-Origin']) > 0)


if __name__ == "__main__":
    unittest.main()
