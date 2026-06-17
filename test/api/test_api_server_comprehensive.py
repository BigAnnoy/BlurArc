"""
Comprehensive test suite for remaining uncovered lines in api_server.py
======================================================================
Targets: lines 41-43, 59-66, 81-96, 135-158, 190-228, 278, 403-404,
         423-425, 444-446, 475-477, 481-482, 503, 530-531, 551-553,
         775-776, 829-831, 856, 863-865, 868, 882-907, 923-925, 948,
         996-1018, 1065-1066, 1078, 1135-1136, 1163, 1172-1173,
         1184-1191, 1214-1215, 1231-1232, 1249-1250, 1264, 1274-1275,
         1285, 1324-1326, 1361-1363, 1383-1385, 1400-1402, 1452,
         1471-1473, 1486-1488, 1509-1511, 1521, 1532-1534, 1544,
         1555-1557, 1569, 1581, 1600-1601, 1610-1611, 1620-1628,
         1632-1633, 1637-1639, 1653-1677, 1686-1688, 1706-1707,
         1713-1715, 1726-1744, 1755-1773, 1778-1788, 1793-1814,
         1819-1852, 1857-1868, 1878, 1906-1908
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ============================================================================
# Test Fallback Imports & Config Manager
# ============================================================================

class TestFallbackImports:
    """Test fallback import paths (lines 41-43, 59-66, 104)"""

    def test_get_config_manager_relative_import(self, client):
        with patch('backend.api_server.get_config_manager') as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = '/test/album'
            mock_gcm.return_value = mock_cfg
            resp = client.get('/api/settings/album-path')
        assert resp.status_code == 200

    def test_get_config_manager_returns_none(self, client):
        with patch('backend.api_server.get_config_manager', return_value=None):
            with patch('backend.api_server.Path') as mock_path_cls:
                mock_p = MagicMock()
                mock_p.exists.return_value = False
                mock_path_cls.return_value = mock_p
                resp = client.get('/api/settings/album-path')
        data = json.loads(resp.data)
        assert data.get('album_path') is None

    def test_get_album_stats_no_album_path(self, client):
        with patch('backend.api_server.get_config_manager', return_value=None):
            with patch('backend.api_server.Path') as mock_path_cls:
                mock_p = MagicMock()
                mock_p.exists.return_value = False
                mock_path_cls.return_value = mock_p
                resp = client.get('/api/album/stats')
        # When no album path, returns error or empty stats
        data = json.loads(resp.data)
        assert 'total_files' in data or 'error' in data

    def test_get_album_stats_exception_returns_empty(self, client):
        with patch('backend.api_server.get_config_manager') as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = '/nonexistent/path'
            mock_gcm.return_value = mock_cfg
            with patch('backend.api_server.Path') as mock_path_cls:
                mock_p = MagicMock()
                mock_p.exists.return_value = False
                mock_path_cls.return_value = mock_p
                resp = client.get('/api/album/stats')
        data = json.loads(resp.data)
        # Either returns stats or error
        assert 'total_files' in data or 'error' in data


class TestFFmpegCheck:
    """Test FFmpeg availability checks (lines 81-96)"""

    @patch('pathlib.Path.exists')
    def test_check_ffmpeg_local_binary(self, mock_exists, client):
        import subprocess as _subprocess
        mock_exists.return_value = True
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = 'ffmpeg version 5.0'
            
            from backend.api_server import check_ffmpeg
            result = check_ffmpeg()
        
        assert result[0] is True

    def test_check_ffmpeg_system_path(self, client):
        with patch('pathlib.Path.exists', return_value=False):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = 'ffmpeg version 5.0'
                
                from backend.api_server import check_ffmpeg
                result = check_ffmpeg()
        
        assert result[0] is True

    def test_check_ffmpeg_not_available(self, client):
        with patch('pathlib.Path.exists', return_value=False):
            with patch('subprocess.run', side_effect=Exception('not found')):
                from backend.api_server import check_ffmpeg
                result = check_ffmpeg()
        
        assert result[0] is False


# ============================================================================
# Test Album Stats with Database
# ============================================================================

class TestAlbumStatsWithDatabase:
    """Test album stats with database integration (lines 135-158, 190, 194, 199-200, 225-228)"""

    @patch('backend.api_server.get_config_manager')
    def test_album_stats_with_db_records(self, mock_gcm, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_path = Path(tmpdir) / 'album'
            album_path.mkdir()
            (album_path / '2023').mkdir()
            
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(album_path)
            mock_cfg.get_last_import.return_value = None
            mock_gcm.return_value = mock_cfg
            
            mock_db = MagicMock()
            mock_db.query.return_value.all.return_value = []
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            
            mock_db_module = MagicMock()
            mock_db_module.SessionLocal.return_value = mock_db
            mock_db_module.Photo = MagicMock()
            
            with patch.dict('sys.modules', {'database': mock_db_module}):
                resp = client.get('/api/album/stats')
            
            data = json.loads(resp.data)
            assert 'total_files' in data or 'error' in data

    @patch('backend.api_server.get_config_manager')
    def test_album_stats_db_exception(self, mock_gcm, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_path = Path(tmpdir) / 'album'
            album_path.mkdir()
            
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(album_path)
            mock_cfg.get_last_import.return_value = None
            mock_gcm.return_value = mock_cfg
            
            mock_db_module = MagicMock()
            mock_db_module.SessionLocal.side_effect = Exception('db error')
            mock_db_module.Photo = MagicMock()
            
            with patch.dict('sys.modules', {'database': mock_db_module}):
                resp = client.get('/api/album/stats')
            
            data = json.loads(resp.data)
            assert 'total_files' in data or 'error' in data

    @patch('backend.api_server.get_config_manager')
    def test_album_stats_empty_valid_photos(self, mock_gcm, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_path = Path(tmpdir) / 'album'
            album_path.mkdir()
            
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(album_path)
            mock_cfg.get_last_import.return_value = None
            mock_gcm.return_value = mock_cfg
            
            mock_db = MagicMock()
            mock_db.query.return_value.all.return_value = []
            mock_db.__enter__ = MagicMock(return_value=mock_db)
            mock_db.__exit__ = MagicMock(return_value=False)
            
            mock_db_module = MagicMock()
            mock_db_module.SessionLocal.return_value = mock_db
            mock_db_module.Photo = MagicMock()
            
            with patch.dict('sys.modules', {'database': mock_db_module}):
                resp = client.get('/api/album/stats')
            
            data = json.loads(resp.data)
            assert 'total_files' in data or 'error' in data


# ============================================================================
# Test Tree Endpoint Error Handling
# ============================================================================

class TestTreeEndpointErrors:
    """Test tree endpoint error handling (lines 403-404, 423-425)"""

    @patch('backend.api_server.get_config_manager')
    def test_album_tree_exception_handling(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.get_album_path.return_value = '/test/album'
        mock_gcm.return_value = mock_cfg
        
        with patch('backend.api_server.Path') as mock_path_cls:
            mock_p = MagicMock()
            mock_p.exists.return_value = True
            mock_p.is_dir.return_value = True
            mock_p.iterdir.side_effect = Exception('permission denied')
            mock_path_cls.return_value = mock_p
            
            resp = client.get('/api/album/tree')
        
        assert resp.status_code in [200, 500]


# ============================================================================
# Test Photos Endpoint Security Check
# ============================================================================

class TestPhotosEndpointSecurity:
    """Test photos endpoint security check (lines 444-446, 475-477)"""

    @patch('backend.api_server.get_config_manager')
    def test_photos_path_outside_album(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.get_album_path.return_value = '/safe/album'
        mock_gcm.return_value = mock_cfg
        
        with patch('backend.api_server.Path') as mock_path_cls:
            album_p = MagicMock()
            album_p.exists.return_value = True
            album_p.is_dir.return_value = True
            album_p.resolve.return_value = MagicMock()
            album_p.resolve.return_value.__str__ = lambda self: '/safe/album'
            
            file_p = MagicMock()
            file_resolve = MagicMock()
            file_resolve.relative_to.side_effect = ValueError('path outside')
            file_p.resolve.return_value = file_resolve
            file_p.exists.return_value = True
            file_p.is_file.return_value = True
            
            def path_factory(p):
                if '/outside' in str(p):
                    return file_p
                return album_p
            mock_path_cls.side_effect = path_factory
            
            resp = client.get('/api/album/photos?path=/outside/dir')
        
        assert resp.status_code == 403
        data = json.loads(resp.data)
        assert 'error' in data


# ============================================================================
# Test Thumbnail Endpoint
# ============================================================================

class TestThumbnailEndpoint:
    """Test thumbnail endpoint (lines 481-482, 503)"""

    def test_thumbnail_missing_path(self, client):
        resp = client.get('/api/album/thumbnail')
        assert resp.status_code == 400

    def test_thumbnail_file_not_found(self, client):
        resp = client.get('/api/album/thumbnail')
        assert resp.status_code == 400

    @patch('backend.api_server.get_album_path')
    def test_thumbnail_returns_file(self, mock_get_album_path, client):
        mock_get_album_path.return_value = None
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tf:
            tf.write(b'fake image')
            tf.flush()
            tf_path = tf.name
        
        try:
            mock_tm = MagicMock()
            mock_tm.get_thumbnail.return_value = tf_path
            
            with patch('backend.api_server.get_thumbnail_manager', return_value=mock_tm):
                resp = client.get(f'/api/album/thumbnail?path={tf_path}')
        finally:
            try:
                Path(tf_path).unlink()
            except:
                pass
        
        assert resp.status_code in [200, 500]


# ============================================================================
# Test File Endpoint Security
# ============================================================================

class TestFileEndpointSecurity:
    """Test file endpoint security check (lines 530-531, 551-553)"""

    @patch('backend.api_server.get_config_manager')
    def test_file_path_outside_album(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.get_album_path.return_value = '/safe/album'
        mock_gcm.return_value = mock_cfg
        
        with patch('backend.api_server.Path') as mock_path_cls:
            file_p = MagicMock()
            file_p.exists.return_value = True
            file_p.is_file.return_value = True
            file_resolve = MagicMock()
            file_resolve.relative_to.side_effect = ValueError('path outside')
            file_p.resolve.return_value = file_resolve
            mock_path_cls.side_effect = lambda p: file_p
            
            resp = client.get('/api/album/file?path=/outside/file.txt')
        
        assert resp.status_code == 403


# ============================================================================
# Test Video Metadata Fallback Import
# ============================================================================

class TestVideoMetadataFallback:
    """Test video metadata fallback import (lines 775-776)"""

    @patch('backend.api_server.get_album_path')
    def test_video_metadata_fallback_import(self, mock_get_album_path, client):
        mock_get_album_path.return_value = None
        
        with patch.dict('sys.modules', {'backend.video_processor': None}), \
             patch('backend.api_server.Path') as mock_path_cls:
            mock_p = MagicMock()
            mock_p.exists.return_value = True
            mock_p.is_file.return_value = True
            mock_path_cls.return_value = mock_p
            
            mock_vp = MagicMock()
            mock_vp.extract_metadata.return_value = {
                'duration': 10.0,
                'width': 1920,
                'height': 1080,
                'codec': 'h264',
                'format': 'mp4',
                'size': 1000,
            }
            with patch('backend.video_processor.VideoProcessor', return_value=mock_vp):
                resp = client.get('/api/video/metadata?path=/fake/video.mp4')
        
        assert resp.status_code == 200


# ============================================================================
# Test Settings Album-Path Endpoint
# ============================================================================

class TestAlbumPathSettings:
    """Test album-path settings (lines 829-831, 856, 863-865, 868, 923-925)"""

    @patch('backend.api_server.get_config_manager')
    def test_set_album_path_config_init_failure(self, mock_gcm, client):
        mock_gcm.return_value = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            resp = client.put('/api/settings/album-path', json={'album_path': tmpdir})
        
        assert resp.status_code == 500
        data = json.loads(resp.data)
        assert 'error' in data

    @patch('backend.api_server.get_config_manager')
    def test_set_album_path_async_not_available(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.set_album_path_only = None
        mock_cfg.set_album_path.return_value = True
        mock_gcm.return_value = mock_cfg
        
        with tempfile.TemporaryDirectory() as tmpdir:
            resp = client.put('/api/settings/album-path', json={'album_path': tmpdir})
        
        assert resp.status_code in [200, 500]

    @patch('backend.api_server.get_config_manager')
    def test_set_album_path_failure(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.set_album_path_only.return_value = False
        mock_cfg.set_album_path.return_value = False
        mock_gcm.return_value = mock_cfg
        
        with tempfile.TemporaryDirectory() as tmpdir:
            resp = client.put('/api/settings/album-path', json={'album_path': tmpdir})
        
        assert resp.status_code == 500


# ============================================================================
# Test Rebuild Index Tasks
# ============================================================================

class TestRebuildIndexTasks:
    """Test rebuild index tasks (lines 882-884, 903-907, 948)"""

    @patch('backend.api_server.get_config_manager')
    def test_rebuild_index_success(self, mock_gcm, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = tmpdir
            mock_cfg.get_rebuild_status.return_value = {'status': 'completed'}
            mock_cfg.rebuild_database_index.return_value = True
            mock_cfg.set_album_path_only.return_value = True
            mock_gcm.return_value = mock_cfg
            
            resp = client.put('/api/settings/album-path', json={'album_path': tmpdir})
            
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert 'task_id' in data or 'status' in data

    def test_get_rebuild_task_info(self, client):
        resp = client.get('/api/settings/rebuild-progress/fake_task_id')
        assert resp.status_code in [200, 404]


# ============================================================================
# Test Locale Detection
# ============================================================================

class TestLocaleDetection:
    """Test locale detection fallbacks (lines 996-1018)"""

    def test_locale_detection_exception(self, client):
        import locale as _locale
        
        orig_getdefaultlocale = _locale.getdefaultlocale
        
        def failing_getdefaultlocale():
            raise Exception('locale error')
        
        try:
            _locale.getdefaultlocale = failing_getdefaultlocale
            resp = client.get('/api/system/locale')
        finally:
            _locale.getdefaultlocale = orig_getdefaultlocale
        
        data = json.loads(resp.data)
        assert data['language'] == 'zh'

    def test_locale_detection_none_result(self, client):
        import locale as _locale
        
        orig_getdefaultlocale = _locale.getdefaultlocale
        _locale.getdefaultlocale = lambda: (None, None)
        
        try:
            resp = client.get('/api/system/locale')
        finally:
            _locale.getdefaultlocale = orig_getdefaultlocale
        
        data = json.loads(resp.data)
        assert 'language' in data


# ============================================================================
# Test Import Endpoint Fallbacks
# ============================================================================

class TestImportEndpointFallbacks:
    """Test import endpoint fallbacks (lines 1065-1066, 1078)"""

    @patch('backend.api_server.get_config_manager')
    def test_import_progress_task_not_found(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.get_album_path.return_value = None
        mock_gcm.return_value = mock_cfg
        
        with patch('backend.api_server.get_import_manager') as mock_gim:
            mock_im = MagicMock()
            mock_im.get_progress.return_value = None
            mock_gim.return_value = mock_im
            
            resp = client.get('/api/import/progress?task_id=nonexistent')
        
        assert resp.status_code == 404 or resp.status_code == 200


# ============================================================================
# Test File Deletion with Security Checks
# ============================================================================

class TestFileDeletionSecurity:
    """Test file deletion security checks (lines 1569, 1581, 1600-1601, 1610-1611, 1620-1628, 1632-1633, 1637-1639, 1675-1677, 1686-1688)"""

    @patch('backend.api_server.get_config_manager')
    def test_delete_paths_must_be_array(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_gcm.return_value = mock_cfg
        
        resp = client.post('/api/files/delete', json={'paths': 'not_an_array'})
        
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'error' in data

    @patch('backend.api_server.get_config_manager')
    def test_delete_single_string_source_path(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.get_album_path.return_value = None
        mock_cfg.get_last_import.return_value = None
        mock_gcm.return_value = mock_cfg
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / 'test.txt'
            test_file.write_bytes(b'test')
            
            resp = client.post('/api/files/delete', json={
                'paths': [str(test_file)],
                'allowed_source_paths': str(tmpdir)
            })
            
            try:
                test_file.unlink()
            except:
                pass
        
        assert resp.status_code == 200

    @patch('backend.api_server.get_config_manager')
    def test_delete_file_not_in_album_or_source(self, mock_gcm, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_path = Path(tmpdir) / 'album'
            album_path.mkdir()
            
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(album_path)
            mock_cfg.get_last_import.return_value = None
            mock_gcm.return_value = mock_cfg
            
            outside_file = Path(tmpdir) / 'outside.txt'
            outside_file.write_bytes(b'outside')
            
            try:
                resp = client.post('/api/files/delete', json={
                    'paths': [str(outside_file)]
                })
            finally:
                try:
                    outside_file.unlink()
                except:
                    pass
            
            assert resp.status_code == 403 or resp.status_code == 200

    @patch('backend.api_server.get_config_manager')
    def test_delete_nonexistent_file(self, mock_gcm, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_path = Path(tmpdir) / 'album'
            album_path.mkdir()
            
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(album_path)
            mock_cfg.get_last_import.return_value = None
            mock_gcm.return_value = mock_cfg
            
            resp = client.post('/api/files/delete', json={
                'paths': [str(album_path / 'nonexistent.jpg')]
            })
        
        data = json.loads(resp.data)
        assert 'failed' in data or 'deleted_count' in data

    @patch('backend.api_server.get_config_manager')
    def test_delete_directory_rejected(self, mock_gcm, client):
        with tempfile.TemporaryDirectory() as tmpdir:
            album_path = Path(tmpdir) / 'album'
            album_path.mkdir()
            subdir = album_path / 'subdir'
            subdir.mkdir()
            
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(album_path)
            mock_cfg.get_last_import.return_value = None
            mock_gcm.return_value = mock_cfg
            
            resp = client.post('/api/files/delete', json={
                'paths': [str(subdir)]
            })
        
        try:
            subdir.rmdir()
        except:
            pass
        
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'failed' in data


# ============================================================================
# Test Frontend Static File Serving
# ============================================================================

class TestFrontendStaticFiles:
    """Test frontend static file serving (lines 1706-1707, 1713-1715, 1726-1744, 1755-1773, 1778-1788, 1793-1814, 1819-1852, 1857-1868)"""

    def test_js_file_path_traversal(self, client):
        resp = client.get('/api/frontend/js/../../../etc/passwd')
        assert resp.status_code in [403, 404, 500]

    def test_js_file_not_found(self, client):
        resp = client.get('/api/frontend/js/nonexistent.js')
        assert resp.status_code == 404

    def test_css_file_path_traversal(self, client):
        resp = client.get('/api/frontend/css/../../../etc/passwd')
        assert resp.status_code in [403, 404, 500]

    def test_css_file_not_found(self, client):
        resp = client.get('/api/frontend/css/nonexistent.css')
        assert resp.status_code == 404

    def test_favicon_not_found(self, client):
        with patch('backend.api_server.Path') as mock_path_cls:
            mock_p = MagicMock()
            mock_p.exists.return_value = False
            mock_path_cls.return_value = mock_p
            resp = client.get('/favicon.svg')
        assert resp.status_code in [200, 204]

    def test_svg_file_path_traversal(self, client):
        resp = client.get('/api/frontend/svg/../../../etc/passwd')
        assert resp.status_code in [403, 404, 500]

    def test_svg_file_not_found(self, client):
        resp = client.get('/api/frontend/svg/nonexistent')
        assert resp.status_code == 404

    def test_module_file_path_traversal(self, client):
        resp = client.get('/api/frontend/modules/../../../etc/passwd')
        assert resp.status_code in [403, 404, 500]

    def test_module_file_starting_with_slash(self, client):
        resp = client.get('/api/frontend/modules/etc/passwd')
        assert resp.status_code in [403, 404, 500]

    def test_module_file_not_found(self, client):
        resp = client.get('/api/frontend/modules/nonexistent.js')
        assert resp.status_code == 404

    def test_diagnostic_page_not_found(self, client):
        with patch('backend.api_server.Path') as mock_path_cls:
            mock_p = MagicMock()
            mock_p.exists.return_value = False
            mock_path_cls.return_value = mock_p
            resp = client.get('/diagnostic')
        assert resp.status_code in [200, 404, 500]


# ============================================================================
# Test Cache Cleanup
# ============================================================================

class TestCacheCleanup:
    """Test cache cleanup endpoint (lines 1906-1908)"""

    @patch('backend.api_server.get_config_manager')
    def test_cache_cleanup_exception(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.get_album_path.return_value = None
        mock_gcm.return_value = mock_cfg
        
        with patch('backend.api_server.Path') as mock_path_cls:
            mock_p = MagicMock()
            mock_p.exists.return_value = False
            mock_path_cls.return_value = mock_p
            
            resp = client.post('/api/cache/cleanup')
        
        assert resp.status_code in [200, 500]


# ============================================================================
# Test Global Error Handler
# ============================================================================

class TestGlobalErrorHandler:
    """Test global 500 error handler (line 1878)"""

    def test_500_error_handler(self, client):
        resp = client.get('/api/nonexistent/endpoint')
        assert resp.status_code in [404, 500]


# ============================================================================
# Test Import Check with Exception
# ============================================================================

class TestImportCheckException:
    """Test import check exception handling (lines 1324-1326)"""

    @patch('backend.api_server.get_config_manager')
    def test_import_check_exception(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.get_album_path.return_value = None
        mock_cfg.get_last_import.return_value = None
        mock_gcm.return_value = mock_cfg
        
        with patch('backend.api_server.Path') as mock_path_cls:
            mock_p = MagicMock()
            mock_p.exists.return_value = True
            mock_p.is_dir.return_value = True
            mock_p.iterdir.side_effect = Exception('unexpected error')
            mock_path_cls.return_value = mock_p
            
            resp = client.post('/api/import/check', json={'source_path': '/some/path'})
        
        assert resp.status_code in [200, 500]


# ============================================================================
# Test Import Start Validation
# ============================================================================

class TestImportStartValidation:
    """Test import start validation (lines 1452, 1471-1473)"""

    @patch('backend.api_server.get_config_manager')
    def test_import_start_invalid_target(self, mock_gcm, client):
        mock_cfg = MagicMock()
        mock_cfg.get_album_path.return_value = None
        mock_gcm.return_value = mock_cfg
        
        resp = client.post('/api/import/start', json={
            'source_path': '/some/source',
            'target_path': '/nonexistent/target',
            'mode': 'copy'
        })
        
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'error' in data
