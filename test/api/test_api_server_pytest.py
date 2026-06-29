"""
API Server 功能测试 (pytest版本)
测试 api_server.py 中的主要 API 端点
"""

import json
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

import pytest


class TestAPIServer:
    """测试 API Server 主要端点"""
    
    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'ok'
        assert 'timestamp' in data
    
    @patch('backend.api_server.get_album_stats')
    def test_album_stats(self, mock_get_album_stats, client):
        """测试相册统计端点"""
        # 模拟成功获取统计信息
        # v0.7 #6 修复后：last_import 由 get_album_stats() 内部从 config.get_last_import() 填充
        mock_stats = {
            'total_files': 100,
            'video_count': 20,
            'total_size': 1024 * 1024 * 100,  # 100MB
            'total_size_mb': 100.0,
            'years': {},
            'last_import': '2023-01-01T00:00:00',
        }
        mock_get_album_stats.return_value = mock_stats

        response = client.get('/api/album/stats')

        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'total_files' in data
        assert data['total_files'] == 100
        assert 'last_import' in data
        assert data['last_import'] == '2023-01-01T00:00:00'

        # 模拟获取统计信息失败
        mock_get_album_stats.return_value = None

        response = client.get('/api/album/stats')

        assert response.status_code == 500

        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('backend.api_server.get_album_path')
    def test_album_tree(self, mock_get_album_path, client):
        """测试目录树端点"""
        # 模拟相册路径不存在
        mock_get_album_path.return_value = '/non/existent/path'
        
        response = client.get('/api/album/tree')
        
        assert response.status_code == 404
        
        # 模拟相册路径存在
        # 注意：这里需要更复杂的模拟，因为 build_tree 函数会实际访问文件系统
        # 我们可以通过 patch Path.exists 来模拟
        with patch('backend.api_server.Path.exists') as mock_exists:
            mock_exists.return_value = True
            mock_get_album_path.return_value = '/valid/album/path'
            
            # 模拟 os.scandir 返回空目录
            with patch('backend.api_server.os.scandir') as mock_scandir:
                mock_scandir.return_value = []
                
                response = client.get('/api/album/tree')
                
                assert response.status_code == 200
    
    def test_album_photos_missing_param(self, client):
        """测试缺少 path 参数的照片列表请求"""
        response = client.get('/api/album/photos')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
        assert '缺少 path 参数' in data['error']
    
    @patch('backend.api_server.get_album_path')
    def test_album_photos_invalid_path(self, mock_get_album_path, client):
        """测试无效路径的照片列表请求"""
        # 模拟相册路径不存在
        mock_get_album_path.return_value = '/album/path'
        
        response = client.get('/api/album/photos?path=/invalid/path')
        
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('backend.api_server.check_ffmpeg')
    def test_get_ffmpeg_status(self, mock_check_ffmpeg, client):
        """测试 FFmpeg 状态端点"""
        # 模拟 FFmpeg 可用
        mock_check_ffmpeg.return_value = (True, '/path/to/ffmpeg')
        
        response = client.get('/api/settings/ffmpeg-status')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'available'
        assert 'path' in data
        assert data['path'] == '/path/to/ffmpeg'
        
        # 模拟 FFmpeg 不可用
        mock_check_ffmpeg.return_value = (False, None)
        
        response = client.get('/api/settings/ffmpeg-status')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'unavailable'
        assert data['path'] is None
    
    @patch('backend.api_server.get_config_manager')
    def test_get_album_path_api(self, mock_get_config_manager, client):
        """测试获取相册路径端点"""
        # 模拟配置管理器返回相册路径
        mock_config = MagicMock()
        mock_config.get_album_path.return_value = '/album/path'
        mock_get_config_manager.return_value = mock_config
        
        response = client.get('/api/settings/album-path')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'album_path' in data
        assert data['album_path'] == '/album/path'
        
        # 模拟配置管理器返回空值
        mock_config.get_album_path.return_value = ''
        
        response = client.get('/api/settings/album-path')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['album_path'] is None
    
    def test_system_locale(self, client):
        """测试系统语言检测端点"""
        response = client.get('/api/system/locale')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'locale' in data
        assert 'language' in data
        # 语言应该是 'zh' 或 'en'
        assert data['language'] in ['zh', 'en']
    
    @patch('backend.api_server.get_thumbnail_manager')
    def test_cache_cleanup(self, mock_get_thumbnail_manager, client):
        """测试缓存清理端点"""
        # 模拟缩略图管理器
        mock_tm = MagicMock()
        mock_tm.cleanup_cache_by_size.return_value = {
            'deleted_count': 10,
            'freed_mb': 50.0,
            'remaining_mb': 450.0
        }
        mock_get_thumbnail_manager.return_value = mock_tm
        
        # 测试默认参数
        response = client.post('/api/cache/cleanup')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'deleted_count' in data
        assert data['deleted_count'] == 10
        
        # 测试无效参数
        response = client.post('/api/cache/cleanup', data=json.dumps({'max_size_mb': 0}), content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('backend.api_server.get_import_manager')
    def test_start_import_missing_params(self, mock_get_import_manager, client):
        """测试缺少参数的导入请求"""
        response = client.post('/api/import/start', data=json.dumps({}), content_type='application/json')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('backend.api_server.get_album_path')
    def test_album_exif_missing_param(self, mock_get_album_path, client):
        """测试缺少 path 参数的 EXIF 请求"""
        mock_get_album_path.return_value = '/album/path'
        
        response = client.get('/api/album/exif')
        
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_not_found(self, client):
        """测试 404 错误处理"""
        response = client.get('/non/existent/endpoint')
        
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert '404 Not Found' in data['error']
    
    def test_index(self, client):
        """测试主页端点"""
        # 这个测试可能会失败，因为它需要实际的前端文件
        # 我们可以通过 patch 来模拟文件读取
        with patch('backend.api_server.Path.exists') as mock_exists:
            mock_exists.return_value = True
            
            with patch('backend.api_server.open', mock_open(read_data='<html></html>')) as mock_file:
                response = client.get('/')
                
                assert response.status_code == 200
                assert 'text/html' in response.content_type
    
    def test_serve_js_invalid_path(self, client):
        """测试无效路径的 JS 文件请求"""
        response = client.get('/js/../invalid.js')
        
        assert response.status_code == 403
        
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_serve_css_invalid_path(self, client):
        """测试无效路径的 CSS 文件请求"""
        response = client.get('/css/../invalid.css')
        
        assert response.status_code == 403
        
        data = json.loads(response.data)
        assert 'error' in data
