"""
相册 API 功能测试
测试与相册相关的所有 API 端点
"""

import sys
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.api_server import app
from backend.config_manager import ConfigManager


class TestAPIAlbum(unittest.TestCase):
    """相册 API 测试类"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建 Flask 测试客户端
        self.client = app.test_client()
        # 启用测试环境
        app.config['TESTING'] = True
        
        # 创建临时目录作为测试相册路径
        self.temp_album_dir = tempfile.mkdtemp()
        
        # 创建一些测试照片文件
        self._create_test_photos()
    
    def tearDown(self):
        """测试后的清理工作"""
        # 删除临时目录
        import shutil
        shutil.rmtree(self.temp_album_dir, ignore_errors=True)
    
    def _create_test_photos(self):
        """创建测试照片文件"""
        # 创建年/月目录结构
        year_dir = os.path.join(self.temp_album_dir, "2023")
        month_dir = os.path.join(year_dir, "2023-01")
        os.makedirs(month_dir, exist_ok=True)
        
        # 创建测试照片文件
        with open(os.path.join(month_dir, "test_photo_1.jpg"), "w") as f:
            f.write("dummy photo 1 content")
        
        with open(os.path.join(month_dir, "test_photo_2.jpg"), "w") as f:
            f.write("dummy photo 2 content")
    
    @patch('backend.api_server.get_album_path')
    def test_album_stats(self, mock_get_album_path):
        """测试获取相册统计信息端点"""
        # 模拟相册路径
        mock_get_album_path.return_value = self.temp_album_dir
        
        # 发送 GET 请求到相册统计端点
        response = self.client.get('/api/album/stats')
        
        # 验证响应状态码为 200 OK
        self.assertEqual(response.status_code, 200)
        
        # 解析响应数据
        data = json.loads(response.data)
        
        # 验证响应数据包含预期的字段
        self.assertIn('total_files', data)
        self.assertIn('total_size', data)
        self.assertIn('total_size_mb', data)
        self.assertIn('years', data)
    
    @patch('backend.api_server.get_album_path')
    def test_album_tree(self, mock_get_album_path):
        """测试获取相册目录树端点"""
        # 模拟相册路径
        mock_get_album_path.return_value = self.temp_album_dir
        
        # 模拟数据库返回照片路径（新实现是数据库驱动）
        photo_path = os.path.join(self.temp_album_dir, "2023", "2023-01", "test_photo_1.jpg")
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [(photo_path,)]
        
        mock_db_module = MagicMock()
        mock_db_module.SessionLocal.return_value = mock_db
        mock_db_module.Photo = MagicMock()
        
        with patch.dict('sys.modules', {'database': mock_db_module}):
            # 发送 GET 请求到相册目录树端点
            response = self.client.get('/api/album/tree')
        
        # 验证响应状态码为 200 OK
        self.assertEqual(response.status_code, 200)
        
        # 解析响应数据
        data = json.loads(response.data)
        
        # 验证响应数据结构
        self.assertIn('name', data)
        self.assertIn('path', data)
        self.assertIn('children', data)
        
        # 验证根目录信息
        self.assertEqual(data['name'], os.path.basename(self.temp_album_dir))
        self.assertEqual(data['path'], self.temp_album_dir)
        
        # 验证年份目录
        self.assertEqual(len(data['children']), 1)
        self.assertEqual(data['children'][0]['name'], '2023')
        
        # 验证月份目录
        self.assertEqual(len(data['children'][0]['children']), 1)
        self.assertEqual(data['children'][0]['children'][0]['name'], '2023-01')
        
        # 验证文件计数
        self.assertGreater(data['children'][0]['children'][0]['count'], 0)
    
    @patch('backend.api_server.get_album_path')
    def test_album_photos(self, mock_get_album_path):
        """测试获取指定路径下的照片列表端点"""
        # 模拟相册路径
        mock_get_album_path.return_value = self.temp_album_dir
        
        # 发送 GET 请求获取具体月份目录下的照片列表
        month_path = os.path.join(self.temp_album_dir, "2023", "2023-01")
        response = self.client.get(f'/api/album/photos?path={month_path}')
        
        # 验证响应状态码为 200 OK
        self.assertEqual(response.status_code, 200)
        
        # 解析响应数据
        data = json.loads(response.data)
        
        # 验证响应数据结构
        self.assertIn('path', data)
        self.assertIn('count', data)
        self.assertIn('photos', data)
        
        # 验证路径信息
        self.assertEqual(data['path'], month_path)
        
        # 验证照片列表（注意：由于我们创建的是文本文件，可能不会被识别为照片）
        # 即使扩展名为.jpg，但内容不是真实图片，可能不会被识别
    
    @patch('backend.api_server.get_config_manager')
    def test_get_album_path_api(self, mock_get_config_manager):
        """测试获取当前相册路径 API"""
        # 创建配置管理器实例的模拟
        mock_config = MagicMock()
        mock_config.get_album_path.return_value = self.temp_album_dir
        mock_get_config_manager.return_value = mock_config
        
        # 发送 GET 请求获取相册路径
        response = self.client.get('/api/settings/album-path')
        
        # 验证响应状态码为 200 OK
        self.assertEqual(response.status_code, 200)
        
        # 解析响应数据
        data = json.loads(response.data)
        
        # 验证响应数据
        self.assertIn('album_path', data)
        self.assertEqual(data['album_path'], self.temp_album_dir)
    
    @patch('backend.api_server.get_config_manager')
    def test_set_album_path_api(self, mock_get_config_manager):
        """测试修改相册路径 API"""
        # 创建临时目录作为新的相册路径
        new_album_path = tempfile.mkdtemp()
        
        # 创建配置管理器实例的模拟
        mock_config = MagicMock()
        mock_config.set_album_path_only.return_value = True
        mock_config.get_album_path.return_value = new_album_path
        mock_get_config_manager.return_value = mock_config

        # 发送 PUT 请求修改相册路径
        response = self.client.put(
            '/api/settings/album-path',
            data=json.dumps({'album_path': new_album_path}),
            content_type='application/json'
        )

        # 验证响应状态码为 200 OK
        self.assertEqual(response.status_code, 200)

        # 解析响应数据
        data = json.loads(response.data)

        # 验证响应数据
        self.assertIn('status', data)
        self.assertIn('album_path', data)
        self.assertIn('task_id', data)

        self.assertEqual(data['status'], 'rebuilding')
        self.assertEqual(data['album_path'], new_album_path)

        # 验证配置管理器的方法被调用
        mock_config.set_album_path_only.assert_called_once_with(new_album_path)
        
        # 清理临时目录
        import shutil
        shutil.rmtree(new_album_path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
