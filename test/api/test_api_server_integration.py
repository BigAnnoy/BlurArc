"""
Integration tests for api_server.py - targeting the largest uncovered code blocks.
Uses real temporary directories and files to avoid complex mocking issues.
"""

import json
import os
import tempfile
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestAlbumStatsRealFiles:
    """Test /api/album/stats with real file operations"""

    def test_album_stats_with_real_files(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some fake photos
            Path(tmpdir, 'photo1.jpg').write_bytes(b'fake1' * 100)
            Path(tmpdir, 'photo2.jpg').write_bytes(b'fake2' * 200)

            mock_config = MagicMock()
            mock_config.get_album_path.return_value = tmpdir
            mock_config.get_last_import.return_value = None

            with patch('backend.api_server.get_config_manager', return_value=mock_config):
                response = client.get('/api/album/stats')
                assert response.status_code == 200
                data = json.loads(response.data)
                assert 'total_files' in data

    def test_album_stats_with_video_files(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'photo1.jpg').write_bytes(b'fake')
            Path(tmpdir, 'video1.mp4').write_bytes(b'fake video')

            mock_config = MagicMock()
            mock_config.get_album_path.return_value = tmpdir
            mock_config.get_last_import.return_value = None

            with patch('backend.api_server.get_config_manager', return_value=mock_config):
                response = client.get('/api/album/stats')
                assert response.status_code == 200


class TestAlbumTreeRealFiles:
    """Test /api/album/tree with real file operations"""

    def test_album_tree_with_subdirs(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / '2024-01'
            subdir.mkdir()
            photo_path = subdir / 'photo.jpg'
            photo_path.write_bytes(b'fake')

            mock_config = MagicMock()
            mock_config.get_album_path.return_value = tmpdir

            # Mock database to return the photo path
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.all.return_value = [(str(photo_path),)]
            
            mock_db_module = MagicMock()
            mock_db_module.SessionLocal.return_value = mock_db
            mock_db_module.Photo = MagicMock()
            
            with patch('backend.api_server.get_config_manager', return_value=mock_config):
                with patch.dict('sys.modules', {'database': mock_db_module}):
                    response = client.get('/api/album/tree')
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    # API returns tree structure directly with 'children' key
                    assert 'children' in data
                    assert data['count'] >= 1

    def test_album_tree_with_mixed_files(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            photo1_path = Path(tmpdir, 'photo1.jpg')
            photo1_path.write_bytes(b'fake1')
            Path(tmpdir, 'readme.txt').write_bytes(b'text')
            sub = Path(tmpdir) / 'sub'
            sub.mkdir()
            photo2_path = sub / 'photo2.jpg'
            photo2_path.write_bytes(b'fake2')
            (sub / 'notes.txt').write_bytes(b'text')

            mock_config = MagicMock()
            mock_config.get_album_path.return_value = tmpdir

            # Mock database to return photo paths
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.all.return_value = [
                (str(photo1_path),),
                (str(photo2_path),)
            ]
            
            mock_db_module = MagicMock()
            mock_db_module.SessionLocal.return_value = mock_db
            mock_db_module.Photo = MagicMock()

            with patch('backend.api_server.get_config_manager', return_value=mock_config):
                with patch.dict('sys.modules', {'database': mock_db_module}):
                    response = client.get('/api/album/tree')
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    # Should have children (sub directory)
                    assert 'children' in data


class TestAlbumPhotosRealFiles:
    """Test /api/album/photos with real files"""

    def test_album_photos_with_mixed_types(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, 'photo1.jpg').write_bytes(b'fake1')
            Path(tmpdir, 'photo2.png').write_bytes(b'fake2')
            Path(tmpdir, 'video.mp4').write_bytes(b'fake video')
            Path(tmpdir, 'readme.txt').write_bytes(b'text')

            with patch('backend.api_server.get_album_path', return_value=tmpdir):
                response = client.get(f'/api/album/photos?path={tmpdir}')
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['count'] == 3  # Only media files, not txt

    def test_album_photos_with_nested_files(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / '2024-01'
            subdir.mkdir()
            (subdir / 'photo.jpg').write_bytes(b'fake')

            with patch('backend.api_server.get_album_path', return_value=tmpdir):
                response = client.get(f'/api/album/photos?path={subdir}')
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['count'] == 1


class TestAlbumFileReal:
    """Test /api/album/file with real file serving"""

    def test_album_file_serve_jpeg(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'photo.jpg'
            test_file.write_bytes(b'fake jpeg data')

            # Mock get_album_path to return tmpdir so file passes validation
            with patch('backend.api_server.get_album_path', return_value=tmpdir), \
                 patch('backend.api_server.send_file') as mock_send:
                mock_send.return_value = ('file content', 200, {'Content-Type': 'image/jpeg'})
                response = client.get(f'/api/album/file?path={test_file}')
                assert response.status_code == 200
                assert 'image/jpeg' in response.content_type

    def test_album_file_serve_mp4(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'video.mp4'
            test_file.write_bytes(b'fake mp4 data')

            # Mock get_album_path to return tmpdir so file passes validation
            with patch('backend.api_server.get_album_path', return_value=tmpdir), \
                 patch('backend.api_server.send_file') as mock_send:
                mock_send.return_value = ('file content', 200, {'Content-Type': 'video/mp4'})
                response = client.get(f'/api/album/file?path={test_file}')
                assert response.status_code == 200
                assert 'video/mp4' in response.content_type


class TestImportCheckRealFiles:
    """Test /api/import/check with real files - lines 1305-1326"""

    def test_import_check_with_real_source(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            (source / 'photo1.jpg').write_bytes(b'fake1')
            (source / 'photo2.jpg').write_bytes(b'fake2')

            response = client.post('/api/import/check', json={'source_path': str(source)})
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'date_folders' in data

    def test_import_check_with_multiple_dates(self, client):
        """Test import check with files from different dates (uses EXIF or mtime)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            (source / 'photo1.jpg').write_bytes(b'fake1')
            (source / 'photo2.jpg').write_bytes(b'fake2')
            (source / 'video.mp4').write_bytes(b'fake video')

            response = client.post('/api/import/check', json={'source_path': str(source)})
            assert response.status_code == 200
            data = json.loads(response.data)
            # API returns 'media_count', not 'total_files'
            assert 'media_count' in data
            assert data['media_count'] == 3

    def test_import_check_empty_directory(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()

            response = client.post('/api/import/check', json={'source_path': str(source)})
            assert response.status_code == 200
            data = json.loads(response.data)
            # API returns 'media_count', not 'total_files'
            assert data['media_count'] == 0

    def test_import_check_with_non_media_files(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            (source / 'photo.jpg').write_bytes(b'fake')
            (source / 'readme.txt').write_bytes(b'text')
            (source / 'script.py').write_bytes(b'code')

            response = client.post('/api/import/check', json={'source_path': str(source)})
            assert response.status_code == 200
            data = json.loads(response.data)
            # API returns 'media_count', not 'total_files'
            assert data['media_count'] == 1  # Only media files


class TestImportCheckWithTarget:
    """Test /api/import/check with target path for duplicate detection"""

    def test_import_check_with_target_duplicates(self, client):
        """Test detecting duplicates when target has same files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            target = Path(tmpdir) / 'target'
            target.mkdir()
            
            # Same content in both
            (source / 'photo.jpg').write_bytes(b'same content')
            (target / 'photo.jpg').write_bytes(b'same content')

            response = client.post('/api/import/check', json={
                'source_path': str(source),
                'target_path': str(target)
            })
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'target_duplicates' in data


class TestSystemLocale:
    """Test /api/system/locale - lines 975-1012"""

    def test_system_locale(self, client):
        response = client.get('/api/system/locale')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'locale' in data or 'language' in data


class TestCacheCleanupReal:
    """Test /api/cache/cleanup - lines 1870-1908"""

    def test_cache_cleanup_success(self, client):
        """Test cache cleanup with real thumbnail manager"""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake cache files
            cache_dir = Path(tmpdir) / 'thumbnails'
            cache_dir.mkdir()
            
            for i in range(5):
                (cache_dir / f'thumb_{i}.jpg').write_bytes(b'fake thumbnail data' * 100)
            
            # Create a real ThumbnailManager but override cache_dir
            with patch('backend.api_server.get_thumbnail_manager') as mock_get_manager:
                from backend.thumbnail_manager import ThumbnailManager
                mock_tm = ThumbnailManager()
                mock_tm.cache_dir = cache_dir
                mock_get_manager.return_value = mock_tm
                
                response = client.post('/api/cache/cleanup', json={'max_size_mb': 0.001})
                assert response.status_code == 200
                data = json.loads(response.data)
                assert 'deleted_count' in data or 'freed_mb' in data


class TestSettingsEndpoints:
    """Test various settings endpoints"""

    def test_get_album_path(self, client):
        mock_config = MagicMock()
        mock_config.get_album_path.return_value = '/test/album'
        with patch('backend.api_server.get_config_manager', return_value=mock_config):
            response = client.get('/api/settings/album-path')
            assert response.status_code == 200

    def test_put_album_path(self, client):
        mock_config = MagicMock()
        mock_config.set_album_path_async.return_value = True
        with patch('backend.api_server.get_config_manager', return_value=mock_config), \
             patch('backend.api_server.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            response = client.put('/api/settings/album-path', json={'album_path': '/test/album'})
            assert response.status_code == 200

    def test_get_language(self, client):
        mock_config = MagicMock()
        mock_config.get_setting.return_value = 'zh'
        with patch('backend.api_server.get_config_manager', return_value=mock_config):
            response = client.get('/api/settings/language')
            assert response.status_code == 200

    def test_put_language(self, client):
        mock_config = MagicMock()
        mock_config.set_setting.return_value = True
        with patch('backend.api_server.get_config_manager', return_value=mock_config):
            response = client.put('/api/settings/language', json={'language': 'en'})
            assert response.status_code == 200


class TestRebuildIndex:
    """Test /api/settings/album-path triggers rebuild index"""

    def test_rebuild_index_start(self, client):
        """Test that setting album path starts rebuild task"""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.set_album_path_only.return_value = True
            mock_config.get_album_path.return_value = tmpdir

            with patch('backend.api_server.get_config_manager', return_value=mock_config):
                response = client.put('/api/settings/album-path', json={'album_path': tmpdir})
                assert response.status_code == 200
                data = json.loads(response.data)
                assert 'task_id' in data or 'status' in data

    def test_rebuild_index_failure(self, client):
        """Test rebuild failure when path is invalid"""
        response = client.put('/api/settings/album-path', json={'album_path': '/nonexistent/path'})
        assert response.status_code == 404

    def test_rebuild_progress(self, client):
        """Test rebuild progress endpoint"""
        response = client.get('/api/settings/rebuild-progress/nonexistent_task')
        assert response.status_code == 404


class TestImportStartRealFiles:
    """Test /api/import/start with real files - lines 1430-1473"""

    def test_import_start_with_real_files(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            target = Path(tmpdir) / 'target'
            target.mkdir()
            (source / 'photo.jpg').write_bytes(b'fake photo')

            response = client.post('/api/import/start', json={
                'source_path': str(source),
                'target_path': str(target),
                'mode': 'copy'
            })
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'import_id' in data

    def test_import_start_move_mode(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / 'source'
            source.mkdir()
            target = Path(tmpdir) / 'target'
            target.mkdir()
            (source / 'photo.jpg').write_bytes(b'fake photo')

            response = client.post('/api/import/start', json={
                'source_path': str(source),
                'target_path': str(target),
                'mode': 'move'
            })
            assert response.status_code == 200


class TestDeleteFilesReal:
    """Test /api/files/delete with real file deletion"""

    def test_delete_single_file(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            # File must be in album directory for security check
            album_path = Path(tmpdir) / 'album'
            album_path.mkdir()
            test_file = album_path / 'test.txt'
            test_file.write_bytes(b'test data')

            # Set album path for the security check
            mock_config = MagicMock()
            mock_config.get_album_path.return_value = str(album_path)
            with patch('backend.api_server.get_config_manager', return_value=mock_config):
                response = client.post('/api/files/delete', json={
                    'paths': [str(test_file)]
                })
                data = json.loads(response.data)
                # Check response indicates success
                assert data.get('deleted_count', 0) == 1 or 'deleted' in data

    def test_delete_multiple_files(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_path = Path(tmpdir) / 'album'
            album_path.mkdir()
            f1 = album_path / 'file1.txt'
            f2 = album_path / 'file2.txt'
            f1.write_bytes(b'file1')
            f2.write_bytes(b'file2')

            mock_config = MagicMock()
            mock_config.get_album_path.return_value = str(album_path)
            with patch('backend.api_server.get_config_manager', return_value=mock_config):
                response = client.post('/api/files/delete', json={
                    'paths': [str(f1), str(f2)]
                })
                data = json.loads(response.data)
                assert data.get('deleted_count', 0) >= 1 or 'deleted' in data

    def test_delete_with_source_paths(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file in source directory
            source_dir = Path(tmpdir) / 'source'
            source_dir.mkdir()
            test_file = source_dir / 'test.txt'
            test_file.write_bytes(b'test')

            response = client.post('/api/files/delete', json={
                'paths': [str(test_file)],
                'source_paths': [str(source_dir)]
            })
            data = json.loads(response.data)
            assert data.get('deleted_count', 0) >= 1 or 'deleted' in data


class TestAlbumPathSettingsReal:
    """Test album-path settings with real path validation"""

    def test_put_album_path_valid_directory(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.set_album_path_async.return_value = True

            with patch('backend.api_server.get_config_manager', return_value=mock_config):
                response = client.put('/api/settings/album-path', json={'album_path': tmpdir})
                assert response.status_code == 200

    def test_put_album_path_invalid_not_dir(self, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'file.txt'
            test_file.write_bytes(b'test')

            response = client.put('/api/settings/album-path', json={'album_path': str(test_file)})
            assert response.status_code == 400
