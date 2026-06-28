"""
缩略图管理器测试 (pytest版本)
测试 thumbnail_manager.py 中的主要功能
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.thumbnail_manager import ThumbnailManager, get_thumbnail_manager


class TestThumbnailManager:
    """测试缩略图管理器"""
    
    @pytest.fixture
    def temp_file(self):
        """创建临时文件"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake jpeg content')
            temp_path = Path(f.name)
        
        yield temp_path
        
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
    
    @pytest.fixture
    def thumbnail_manager(self):
        """创建缩略图管理器实例"""
        return ThumbnailManager()
    
    def test_initialization(self):
        """测试缩略图管理器初始化"""
        manager = ThumbnailManager()
        assert manager is not None
        assert isinstance(manager, ThumbnailManager)
        assert manager.thumbnail_size == (200, 200)  # 默认尺寸
    
    def test_get_thumbnail_size(self):
        """测试获取缩略图尺寸"""
        # 测试默认尺寸
        manager = ThumbnailManager()
        assert manager.thumbnail_size == (200, 200)
        
        # 测试自定义尺寸
        with patch('backend.config_manager.get_config_manager') as mock_get_config:
            mock_config = MagicMock()
            mock_config.get_setting.return_value = '300x300'
            mock_get_config.return_value = mock_config
            
            manager = ThumbnailManager()
            assert manager.thumbnail_size == (300, 300)
    
    def test_generate_cache_key(self, thumbnail_manager, temp_file):
        """测试生成缓存键"""
        cache_key = thumbnail_manager._generate_cache_key(temp_file)
        assert cache_key is not None
        assert isinstance(cache_key, str)
        assert len(cache_key) == 32  # MD5哈希长度
    
    def test_get_thumbnail_nonexistent_file(self, thumbnail_manager):
        """测试获取不存在文件的缩略图"""
        result = thumbnail_manager.get_thumbnail('/non/existent/path.jpg')
        assert result is None
    
    def test_get_thumbnail_directory(self, thumbnail_manager, temp_file):
        """测试获取目录的缩略图"""
        with patch('backend.thumbnail_manager.Path.is_file') as mock_is_file:
            mock_is_file.return_value = False
            result = thumbnail_manager.get_thumbnail(str(temp_file))
            assert result is None
    
    @patch('backend.thumbnail_manager.ThumbnailManager._generate_thumbnail_sync')
    def test_get_thumbnail_async(self, mock_generate_sync, thumbnail_manager, temp_file):
        """测试异步获取缩略图"""
        # 模拟缓存不存在，异步生成
        with patch('backend.thumbnail_manager.Path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('backend.thumbnail_manager.Path.is_file') as mock_is_file:
                mock_is_file.return_value = True
                with patch('backend.thumbnail_manager.Path.stat') as mock_stat:
                    mock_stat.return_value = MagicMock(st_mtime=123, st_size=456)
                    with patch('backend.thumbnail_manager.Path.exists') as mock_cache_exists:
                        mock_cache_exists.return_value = False
                        
                        result = thumbnail_manager.get_thumbnail(str(temp_file))
                        assert result is None
    
    @patch('backend.thumbnail_manager.Image.open')
    def test_get_preview_jpeg_native_format(self, mock_image_open, thumbnail_manager, temp_file):
        """测试获取原生格式的预览图"""
        result = thumbnail_manager.get_preview_jpeg(str(temp_file))
        assert result == temp_file
        mock_image_open.assert_not_called()
    
    @patch('backend.thumbnail_manager.Image.open')
    def test_get_preview_jpeg_convert_format(self, mock_image_open, thumbnail_manager, temp_file):
        """测试获取需要转换格式的预览图"""
        # 创建一个模拟的HEIC文件路径
        heic_path = temp_file.with_suffix('.heic')
        
        # 模拟文件存在
        with patch('backend.thumbnail_manager.Path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('backend.thumbnail_manager.Path.is_file') as mock_is_file:
                mock_is_file.return_value = True
                with patch('backend.thumbnail_manager.Path.stat') as mock_stat:
                    mock_stat.return_value = MagicMock(st_mtime=123, st_size=456)
                    
                    # 模拟图片处理
                    mock_img = MagicMock()
                    mock_img.mode = 'RGB'
                    mock_img.thumbnail.return_value = None
                    mock_image_open.return_value.__enter__.return_value = mock_img
                    
                    result = thumbnail_manager.get_preview_jpeg(str(heic_path))
                    assert result is not None
                    assert result.exists()
    
    def test_cleanup_cache_by_size(self, thumbnail_manager):
        """测试按大小清理缓存"""
        # 测试空缓存目录
        result = thumbnail_manager.cleanup_cache_by_size(max_size_mb=100)
        assert result['deleted_count'] == 0
        assert result['freed_mb'] == 0.0
    
    def test_get_thumbnail_manager_singleton(self):
        """测试单例模式"""
        manager1 = get_thumbnail_manager()
        manager2 = get_thumbnail_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, ThumbnailManager)
    
    def test_generate_cache_key_different_files(self, thumbnail_manager, temp_file):
        """测试不同文件生成不同的缓存键"""
        # 创建另一个临时文件
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'another fake jpeg content')
            temp_path2 = Path(f.name)
        
        cache_key1 = thumbnail_manager._generate_cache_key(temp_file)
        cache_key2 = thumbnail_manager._generate_cache_key(temp_path2)
        
        assert cache_key1 != cache_key2
        
        # 清理第二个临时文件
        temp_path2.unlink()
    
    def test_browser_native_exts(self):
        """测试浏览器原生支持的格式列表"""
        manager = ThumbnailManager()
        assert manager.BROWSER_NATIVE_EXTS == {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    
    def test_convert_exts(self):
        """测试需要转换的格式列表"""
        manager = ThumbnailManager()
        assert manager.CONVERT_EXTS == {'.heic', '.heif', '.tiff', '.tif', '.bmp', '.ico'}
    
    @patch('backend.thumbnail_manager.VideoProcessor.generate_thumbnail')
    def test_generate_video_thumbnail(self, mock_generate_video_thumb, thumbnail_manager, temp_file):
        """测试生成视频缩略图"""
        # 创建视频文件路径
        video_path = temp_file.with_suffix('.mp4')
        
        # 模拟文件存在
        with patch('backend.thumbnail_manager.Path.exists') as mock_exists:
            mock_exists.return_value = True
            
            # 模拟视频缩略图生成成功
            mock_generate_video_thumb.return_value = True
            
            result = thumbnail_manager._generate_video_thumbnail(video_path, Path('output.jpg'))
            assert result == Path('output.jpg')
    
    @patch('backend.thumbnail_manager.Image.open')
    def test_generate_image_thumbnail(self, mock_image_open, thumbnail_manager, temp_file):
        """测试生成图片缩略图"""
        # 模拟图片处理
        mock_img = MagicMock()
        mock_img.mode = 'RGB'
        mock_img.thumbnail.return_value = None
        mock_image_open.return_value.__enter__.return_value = mock_img
        
        result = thumbnail_manager._generate_image_thumbnail(temp_file, Path('output.jpg'))
        assert result == Path('output.jpg')
    
    def test_get_thumbnail_sync_nonexistent(self, thumbnail_manager):
        """测试同步获取不存在文件的缩略图"""
        result = thumbnail_manager.get_thumbnail_sync('/non/existent/path.jpg')
        assert result is None
    
    def test_get_preview_jpeg_nonexistent_file(self, thumbnail_manager):
        """测试获取不存在文件的预览图"""
        result = thumbnail_manager.get_preview_jpeg('/non/existent/path.jpg')
        assert result is None

    def test_get_thumbnail_manager(self):
        """测试获取全局缩略图管理器"""
        manager = get_thumbnail_manager()
        assert manager is not None
        assert isinstance(manager, ThumbnailManager)
        
        # 再次获取，测试单例模式
        manager2 = get_thumbnail_manager()
        assert manager is manager2
    
    @patch('backend.thumbnail_manager.Image.open')
    def test_generate_image_thumbnail_with_different_modes(self, mock_image_open, thumbnail_manager, temp_file):
        """测试不同图片模式的缩略图生成"""
        # 测试 RGBA 模式
        mock_img_rgba = MagicMock()
        mock_img_rgba.mode = 'RGBA'
        mock_img_rgba.split.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_image_open.return_value.__enter__.return_value = mock_img_rgba
        
        result = thumbnail_manager._generate_image_thumbnail(temp_file, Path('output_rgba.jpg'))
        assert result == Path('output_rgba.jpg')
        
        # 测试 P 模式带透明通道
        mock_img_p = MagicMock()
        mock_img_p.mode = 'P'
        mock_img_p.info = {'transparency': True}
        mock_img_p.split.return_value = [MagicMock()]
        
        # 模拟 convert('RGBA') 返回一个新的 MagicMock
        mock_img_rgba_new = MagicMock()
        mock_img_rgba_new.mode = 'RGBA'
        mock_img_rgba_new.split.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_img_p.convert.return_value = mock_img_rgba_new
        mock_image_open.return_value.__enter__.return_value = mock_img_p
        
        result = thumbnail_manager._generate_image_thumbnail(temp_file, Path('output_p.jpg'))
        assert result == Path('output_p.jpg')
    
    def test_cleanup_cache(self, thumbnail_manager):
        """测试清理缓存"""
        # 测试清理功能不会抛出异常
        try:
            thumbnail_manager.cleanup_cache(max_age_days=30)
            assert True  # 没有抛出异常
        except Exception as e:
            assert False, f"cleanup_cache 抛出异常: {e}"
    
    def test_generate_thumbnails_batch(self, thumbnail_manager, temp_file):
        """测试批量生成缩略图"""
        # 模拟executor.submit方法，使其同步执行
        with patch.object(thumbnail_manager.executor, 'submit', side_effect=lambda func, *args, **kwargs: func(*args, **kwargs)) as mock_submit:
            # 测试批量生成功能不会抛出异常
            try:
                thumbnail_manager.generate_thumbnails_batch([str(temp_file)])
                assert True  # 没有抛出异常
            except Exception as e:
                assert False, f"generate_thumbnails_batch 抛出异常: {e}"
    
    def test_get_preview_jpeg_other_format(self, thumbnail_manager, temp_file):
        """测试获取其他格式文件的预览图"""
        # 创建视频文件路径
        video_path = temp_file.with_suffix('.mp4')
        
        # 模拟文件存在
        with patch('backend.thumbnail_manager.Path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('backend.thumbnail_manager.Path.is_file') as mock_is_file:
                mock_is_file.return_value = True
                
                result = thumbnail_manager.get_preview_jpeg(str(video_path))
                assert result is None  # 视频格式返回None
