"""
Extended API Server tests - targeting uncovered lines
Uses real file operations and minimal mocking for reliability.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestAlbumThumbnailExtended:
    """Test GET /api/album/thumbnail - lines 488-509"""

    def test_thumbnail_missing_path_param(self, client):
        response = client.get('/api/album/thumbnail')
        assert response.status_code == 400

    def test_thumbnail_generation_failure(self, client):
        mock_manager = MagicMock()
        mock_manager.get_thumbnail_sync.return_value = None
        with patch('backend.api_server.get_thumbnail_manager', return_value=mock_manager):
            response = client.get('/api/album/thumbnail?path=%2Ffake%2Fphoto.jpg')
            assert response.status_code == 400

    def test_thumbnail_exception(self, client):
        mock_manager = MagicMock()
        mock_manager.get_thumbnail_sync.side_effect = Exception("disk error")
        with patch('backend.api_server.get_thumbnail_manager', return_value=mock_manager):
            response = client.get('/api/album/thumbnail?path=%2Ffake%2Fphoto.jpg')
            assert response.status_code == 500


class TestAlbumFileExtended:
    """Test GET /api/album/file - lines 514-553"""

    def test_file_missing_path_param(self, client):
        response = client.get('/api/album/file')
        assert response.status_code == 400

    def test_file_not_found(self, client):
        with patch('backend.api_server.Path') as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            response = client.get('/api/album/file?path=%2Ftmp%2Fnonexist.jpg')
            assert response.status_code == 404


class TestAlbumExifExtended:
    """Test GET /api/album/exif - lines 577-693"""

    def test_exif_missing_path_param(self, client):
        response = client.get('/api/album/exif')
        assert response.status_code == 400

    def test_exif_file_not_found(self, client):
        with patch('backend.api_server.Path') as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            response = client.get('/api/album/exif?path=%2Ftmp%2Fnonexist.jpg')
            assert response.status_code == 404


class TestAlbumPreviewExtended:
    """Test GET /api/album/preview - lines 703-747"""

    def test_preview_missing_path(self, client):
        response = client.get('/api/album/preview')
        assert response.status_code == 400

    def test_preview_file_not_found(self, client):
        with patch('backend.api_server.Path') as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            response = client.get('/api/album/preview?path=%2Ftmp%2Fnonexist.jpg')
            assert response.status_code == 404


class TestVideoMetadataExtended:
    """Test GET /api/video/metadata - lines 753-816"""

    def test_video_metadata_missing_path(self, client):
        response = client.get('/api/video/metadata')
        assert response.status_code == 400

    def test_video_metadata_file_not_found(self, client):
        with patch('backend.api_server.Path') as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = False
            response = client.get('/api/video/metadata?path=%2Ftmp%2Fnonexist.mp4')
            assert response.status_code == 404


class TestAlbumPhotosExtended:
    """Test GET /api/album/photos - lines 429-477"""

    def test_album_photos_missing_param(self, client):
        response = client.get('/api/album/photos')
        assert response.status_code == 400


class TestAlbumStatsExtended:
    """Test GET /api/album/stats - lines 128-284"""

    def test_album_stats_exception(self, client):
        with patch('backend.api_server.get_config_manager', side_effect=Exception("fail")):
            response = client.get('/api/album/stats')
            assert response.status_code == 500


class TestAlbumTreeExtended:
    """Test GET /api/album/tree - lines 295-425"""

    def test_album_tree_no_album_path(self, client):
        with patch('backend.api_server.get_config_manager') as mock_cm:
            mock_cm.return_value.get_album_path.return_value = None
            response = client.get('/api/album/tree')
            assert response.status_code == 404


class TestImportCheckExtended:
    """Test POST /api/import/check - lines 1305-1326"""

    def test_import_check_missing_param(self, client):
        response = client.post('/api/import/check', json={})
        assert response.status_code == 400

    def test_import_check_source_not_dir(self, client):
        with patch('backend.api_server.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.is_dir.return_value = False
            response = client.post('/api/import/check', json={'source_path': '/tmp/fake'})
            assert response.status_code == 400


class TestImportStartExtended:
    """Test POST /api/import/start - lines 1430-1473"""

    def test_import_start_missing_source(self, client):
        response = client.post('/api/import/start', json={'target_path': '/tmp/target'})
        assert response.status_code == 400

    def test_import_start_missing_target(self, client):
        response = client.post('/api/import/start', json={'source_path': '/tmp/source'})
        assert response.status_code == 400

    def test_import_start_source_not_dir(self, client):
        with patch('backend.api_server.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.is_dir.return_value = False
            response = client.post('/api/import/start', json={'source_path': '/tmp/src', 'target_path': '/tmp/tgt'})
            assert response.status_code == 400


class TestAlbumPathSettingsExtended:
    """Test /api/settings/album-path - lines 820-925"""

    def test_put_album_path_missing_param(self, client):
        response = client.put('/api/settings/album-path', json={})
        assert response.status_code == 400


class TestRebuildIndexTask:
    """Test /api/settings/rebuild-index/status - lines 942-948"""

    def test_rebuild_index_task_not_found(self, client):
        mock_config = MagicMock()
        mock_config.get_rebuild_task.return_value = None
        with patch('backend.api_server.get_config_manager', return_value=mock_config):
            response = client.get('/api/settings/rebuild-index/status/nonexistent')
            assert response.status_code == 404


class TestLanguageSettingsExtended:
    """Test language settings endpoints - lines 1016-1047"""

    def test_get_language_preference_exception(self, client):
        with patch('backend.api_server.get_config_manager', side_effect=Exception("fail")):
            response = client.get('/api/settings/language')
            assert response.status_code == 500

    def test_put_language_exception(self, client):
        with patch('backend.api_server.get_config_manager', side_effect=Exception("fail")):
            response = client.put('/api/settings/language', json={'language': 'en'})
            assert response.status_code == 500


class TestDeleteFilesExtended:
    """Test POST /api/files/delete - lines 1559-1688"""

    def test_delete_files_missing_param(self, client):
        response = client.post('/api/files/delete', json={})
        assert response.status_code == 400

    def test_delete_files_empty_list(self, client):
        response = client.post('/api/files/delete', json={'paths': []})
        assert response.status_code == 400

    def test_delete_files_nonexistent(self, client):
        response = client.post('/api/files/delete', json={'paths': ['/nonexistent/file.txt']})
        data = json.loads(response.data)
        assert data['status'] == 'completed'
        assert data['failed_count'] == 1


class TestServeStaticFiles:
    """Test static file serving - various lines"""

    def test_index_route(self, client):
        response = client.get('/')
        assert response.status_code in [200, 404]


class TestFfmpegStatusExtended:
    """Test /api/ffmpeg-status and /api/settings/ffmpeg-status - lines 952-973"""

    def test_settings_ffmpeg_status_basic(self, client):
        response = client.get('/api/settings/ffmpeg-status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data

    def test_settings_ffmpeg_status_exception(self, client):
        with patch('backend.api_server.check_ffmpeg', side_effect=Exception("fail")):
            response = client.get('/api/settings/ffmpeg-status')
            assert response.status_code == 500
