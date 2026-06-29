"""
相册 API 功能测试 (pytest版本)
测试 api_server.py 中的相册相关 API 端点
"""

import json
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest


class TestAPIAlbum:
    """测试相册相关 API 端点"""
    
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
        with patch('backend.api_server.Path.exists') as mock_exists:
            mock_exists.return_value = True
            mock_get_album_path.return_value = '/valid/album/path'
            
            # 模拟 os.scandir 返回空目录
            with patch('backend.api_server.os.scandir') as mock_scandir:
                mock_scandir.return_value = []
                
                response = client.get('/api/album/tree')
                
                assert response.status_code == 200
    
    @patch('backend.api_server.get_album_path')
    def test_album_photos(self, mock_get_album_path, client):
        """测试照片列表端点"""
        # 模拟相册路径
        mock_get_album_path.return_value = '/album/path'
        
        # 模拟目标路径存在且是目录
        with patch('backend.api_server.Path.exists') as mock_exists:
            with patch('backend.api_server.Path.is_dir') as mock_is_dir:
                mock_exists.return_value = True
                mock_is_dir.return_value = True
                
                # 模拟 Path.iterdir 返回空列表
                with patch('backend.api_server.Path.iterdir') as mock_iterdir:
                    mock_iterdir.return_value = []
                    
                    response = client.get('/api/album/photos?path=/album/path')
                    
                    assert response.status_code == 200
                    
                    data = json.loads(response.data)
                    assert 'photos' in data
                    assert len(data['photos']) == 0
    
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
    
    @patch('backend.api_server.get_config_manager')
    def test_set_album_path_api(self, mock_get_config_manager, client):
        """测试设置相册路径端点"""
        # 模拟配置管理器
        mock_config = MagicMock()
        mock_config.set_album_path_only.return_value = True
        mock_get_config_manager.return_value = mock_config
        
        # 测试有效的相册路径
        with patch('backend.api_server.Path.exists') as mock_exists:
            with patch('backend.api_server.Path.is_dir') as mock_is_dir:
                mock_exists.return_value = True
                mock_is_dir.return_value = True
                
                response = client.put(
                    '/api/settings/album-path',
                    data=json.dumps({'album_path': '/new/album/path'}),
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert 'status' in data
                assert 'album_path' in data
                assert 'task_id' in data
        
        # 测试无效的相册路径（不存在）
        with patch('backend.api_server.Path.exists') as mock_exists:
            mock_exists.return_value = False
            
            response = client.put(
                '/api/settings/album-path',
                data=json.dumps({'album_path': '/non/existent/path'}),
                content_type='application/json'
            )
            
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert 'error' in data
        
        # 测试无效的相册路径（不是目录）
        with patch('backend.api_server.Path.exists') as mock_exists:
            with patch('backend.api_server.Path.is_dir') as mock_is_dir:
                mock_exists.return_value = True
                mock_is_dir.return_value = False
                
                response = client.put(
                    '/api/settings/album-path',
                    data=json.dumps({'album_path': '/path/to/file'}),
                    content_type='application/json'
                )
                
                assert response.status_code == 400
                
                data = json.loads(response.data)
                assert 'error' in data