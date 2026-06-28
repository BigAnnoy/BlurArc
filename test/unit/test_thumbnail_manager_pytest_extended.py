"""
Extended test suite for thumbnail_manager.py (67% -> 90%)
=========================================================
Targets: lines 23-24, 65-69, 94-106, 126-127, 135-136, 162-171,
         190-198, 216-218, 243-248, 265-267, 308-309, 319-341,
         375-378, 382-383, 412-413, 427, 434-435, 449-451
"""

import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestThumbnailManagerInit:
    """Test initialization and config (lines 23-24, 65-69)"""

    def test_get_thumbnail_size_exception(self):
        from backend.thumbnail_manager import ThumbnailManager
        
        with patch('backend.config_manager.get_config_manager', side_effect=Exception('config error')):
            manager = ThumbnailManager()
        
        assert manager.thumbnail_size == (200, 200)

    def test_get_thumbnail_size_invalid_format(self):
        from backend.thumbnail_manager import ThumbnailManager
        
        mock_cfg = MagicMock()
        mock_cfg.get_setting.return_value = 'invalid'
        
        with patch('backend.config_manager.get_config_manager', return_value=mock_cfg):
            manager = ThumbnailManager()
        
        assert manager.thumbnail_size == (200, 200)


class TestThumbnailGeneration:
    """Test thumbnail generation (lines 94-106, 126-127, 135-136, 162-171, 190-198, 216-218)"""

    def test_get_thumbnail_nonexistent_file(self):
        from backend.thumbnail_manager import ThumbnailManager
        manager = ThumbnailManager()
        result = manager.get_thumbnail('/nonexistent/file.jpg')
        assert result is None

    def test_get_thumbnail_sync_not_a_file(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ThumbnailManager()
            result = manager.get_thumbnail_sync(tmpdir)
        assert result is None

    def test_get_thumbnail_sync_cache_exists(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            img_file = Path(tmpdir) / 'test.jpg'
            img_file.write_bytes(b'\xff\xd8\xff\xe0' + b'0' * 100)
            
            # Pre-create cache
            cache_file = cache_dir / 'fake_cache.jpg'
            cache_file.write_bytes(b'cache data')
            
            manager = ThumbnailManager()
            manager.cache_dir = cache_dir
            
            # Mock _generate_cache_key to return 'fake_cache'
            with patch.object(manager, '_generate_cache_key', return_value='fake_cache'):
                result = manager.get_thumbnail_sync(str(img_file))
            
            assert result == cache_file

    def test_generate_thumbnail_unsupported_type(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            txt_file = Path(tmpdir) / 'test.txt'
            txt_file.write_bytes(b'text data')
            
            manager = ThumbnailManager()
            manager.image_extensions = set()
            manager.video_extensions = set()
            
            result = manager._generate_thumbnail_sync(txt_file, Path(tmpdir) / 'out.jpg')
            assert result is None

    def test_generate_image_thumbnail_rgba_mode(self):
        from backend.thumbnail_manager import ThumbnailManager
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create RGBA image
            img = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
            img_path = Path(tmpdir) / 'rgba.png'
            img.save(str(img_path))
            
            output_path = Path(tmpdir) / 'thumb.jpg'
            
            manager = ThumbnailManager()
            manager.thumbnail_size = (50, 50)
            
            result = manager._generate_image_thumbnail(img_path, output_path)
            assert result == output_path
            assert output_path.exists()

    def test_generate_image_thumbnail_palette_mode(self):
        from backend.thumbnail_manager import ThumbnailManager
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create palette mode image with transparency
            img = Image.new('P', (100, 100))
            img.info['transparency'] = 128
            img_path = Path(tmpdir) / 'palette.png'
            img.save(str(img_path))
            
            output_path = Path(tmpdir) / 'thumb.jpg'
            
            manager = ThumbnailManager()
            manager.thumbnail_size = (50, 50)
            
            result = manager._generate_image_thumbnail(img_path, output_path)
            assert result is not None

    def test_generate_image_thumbnail_exception(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / 'bad.jpg'
            bad_file.write_bytes(b'not an image')
            
            output_path = Path(tmpdir) / 'thumb.jpg'
            
            manager = ThumbnailManager()
            manager.thumbnail_size = (50, 50)
            
            result = manager._generate_image_thumbnail(bad_file, output_path)
            assert result is None


class TestVideoThumbnail:
    """Test video thumbnail generation (lines 243-248)"""

    def test_generate_video_thumbnail_failure(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            video_file = Path(tmpdir) / 'test.mp4'
            video_file.write_bytes(b'fake video')
            
            output_path = Path(tmpdir) / 'thumb.jpg'
            
            with patch('backend.thumbnail_manager.VideoProcessor') as mock_vp:
                mock_vp.generate_thumbnail.return_value = False
                
                manager = ThumbnailManager()
                result = manager._generate_video_thumbnail(video_file, output_path)
            
            assert result is None


class TestPreviewJPEG:
    """Test preview JPEG conversion (lines 308-309, 319-341)"""

    def test_get_preview_jpeg_native_format(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            jpg_file = Path(tmpdir) / 'test.jpg'
            jpg_file.write_bytes(b'fake jpg')
            
            manager = ThumbnailManager()
            result = manager.get_preview_jpeg(str(jpg_file))
            
            assert result == jpg_file

    def test_get_preview_jpeg_nonexistent(self):
        from backend.thumbnail_manager import ThumbnailManager
        manager = ThumbnailManager()
        result = manager.get_preview_jpeg('/nonexistent.heic')
        assert result is None

    def test_get_preview_jpeg_oserror_fallback(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            heic_file = Path(tmpdir) / 'test.heic'
            heic_file.write_bytes(b'fake heic')
            
            manager = ThumbnailManager()
            manager.cache_dir = Path(tmpdir) / 'cache'
            manager.cache_dir.mkdir()
            
            # Create a mock file path object that will raise OSError on stat
            mock_file_path = MagicMock()
            mock_file_path.exists.return_value = True
            mock_file_path.is_file.return_value = True
            mock_file_path.suffix = '.heic'
            mock_file_path.stat.side_effect = OSError('stat error')
            mock_file_path.__str__ = lambda self: str(heic_file)
            
            # Patch Path constructor to return our mock
            with patch('backend.thumbnail_manager.Path', return_value=mock_file_path):
                result = manager.get_preview_jpeg(str(heic_file))
            
            # Returns None because stat fails before conversion
            assert result is None

    def test_get_preview_jpeg_convert_success(self):
        from backend.thumbnail_manager import ThumbnailManager
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid TIFF file
            img = Image.new('RGB', (100, 100), (255, 0, 0))
            tiff_path = Path(tmpdir) / 'test.tiff'
            img.save(str(tiff_path))
            
            manager = ThumbnailManager()
            manager.cache_dir = Path(tmpdir) / 'cache'
            manager.cache_dir.mkdir()
            
            result = manager.get_preview_jpeg(str(tiff_path))
            
            assert result is not None
            assert result.exists()
            assert result.suffix == '.jpg'

    def test_get_preview_jpeg_video_returns_none(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            mp4_file = Path(tmpdir) / 'test.mp4'
            mp4_file.write_bytes(b'fake video')
            
            manager = ThumbnailManager()
            result = manager.get_preview_jpeg(str(mp4_file))
            
            assert result is None


class TestCacheCleanup:
    """Test cache cleanup methods (lines 375-378, 382-383, 412-413, 427, 434-435, 449-451)"""

    def test_cleanup_cache_by_size_under_limit(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            # Create small cache files
            for i in range(3):
                f = cache_dir / f'test{i}.jpg'
                f.write_bytes(b'x' * 100)
            
            manager = ThumbnailManager()
            manager.cache_dir = cache_dir
            
            result = manager.cleanup_cache_by_size(max_size_mb=1)
            
            assert result['deleted_count'] == 0

    def test_cleanup_cache_by_size_over_limit(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            # Create large cache files
            for i in range(5):
                f = cache_dir / f'test{i}.jpg'
                f.write_bytes(b'x' * 100000)  # 100KB each
            
            manager = ThumbnailManager()
            manager.cache_dir = cache_dir
            
            # Set limit to 300KB (should delete some files)
            result = manager.cleanup_cache_by_size(max_size_mb=0.3)
            
            assert result['deleted_count'] > 0

    def test_cleanup_cache_by_size_exception_during_stat(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            # Create a file
            f = cache_dir / 'test.jpg'
            f.write_bytes(b'test')
            
            manager = ThumbnailManager()
            manager.cache_dir = cache_dir
            
            # Mock the Path.stat method to raise exception only for the test file
            orig_stat = Path.stat
            def failing_stat(p):
                if 'test.jpg' in str(p):
                    raise Exception('stat error')
                return orig_stat(p)
            
            with patch.object(Path, 'stat', failing_stat):
                result = manager.cleanup_cache_by_size(max_size_mb=0.001)
            
            assert 'deleted_count' in result

    def test_cleanup_cache_by_size_exception_during_unlink(self):
        from backend.thumbnail_manager import ThumbnailManager
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / 'cache'
            cache_dir.mkdir()
            
            manager = ThumbnailManager()
            manager.cache_dir = cache_dir
            
            # Create a large file
            f = cache_dir / 'test.jpg'
            f.write_bytes(b'x' * 1000000)  # 1MB
            
            # Mock unlink to fail only for test.jpg
            orig_unlink = Path.unlink
            def failing_unlink(p, *args, **kwargs):
                if 'test.jpg' in str(p):
                    raise PermissionError('cannot delete')
                return orig_unlink(p, *args, **kwargs)
            
            with patch.object(Path, 'unlink', failing_unlink):
                result = manager.cleanup_cache_by_size(max_size_mb=0.001)
            
            assert result['deleted_count'] == 0

    def test_cleanup_cache_by_size_main_exception(self):
        from backend.thumbnail_manager import ThumbnailManager
        
        manager = ThumbnailManager()
        manager.cache_dir = Path('/nonexistent/dir')
        
        result = manager.cleanup_cache_by_size(max_size_mb=1)
        
        assert 'error' in result
        assert result['deleted_count'] == 0

    def test_cleanup_cache_exception_in_iterdir(self):
        from backend.thumbnail_manager import ThumbnailManager
        
        manager = ThumbnailManager()
        manager.cache_dir = MagicMock()
        manager.cache_dir.iterdir.side_effect = Exception('dir error')
        
        manager.cleanup_cache(max_age_days=30)
        # Should not raise exception
