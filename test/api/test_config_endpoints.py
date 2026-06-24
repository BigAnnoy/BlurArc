"""
配置 + 系统端点测试

实际 api_server.py 实现：
- GET  /api/settings/album-path          获取相册路径
- PUT  /api/settings/album-path          设置相册路径（异步重建索引）
- GET  /api/settings/rebuild-progress/<task_id>
- POST /api/settings/rebuild-index       强制重建索引
- GET  /api/settings/ffmpeg-status
- GET  /api/settings/language, PUT /api/settings/language
- GET  /api/settings/theme,    PUT /api/settings/theme
- GET  /api/system/locale
- GET  /api/test

注意：plan 中的 /api/config (GET/PUT) 和 /api/config/reset 端点不存在。
"""
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestAlbumPathEndpoint:
    """GET / PUT /api/settings/album-path"""

    def test_get_album_path(self, client):
        """获取相册路径"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = "/tmp/album"
            mock_gcm.return_value = mock_cfg
            resp = client.get("/api/settings/album-path")
        assert resp.status_code == 200
        body = resp.json
        assert "album_path" in body
        assert body["album_path"] == "/tmp/album"

    def test_get_album_path_unset(self, client):
        """未设置时应返回 None"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = None
            mock_gcm.return_value = mock_cfg
            resp = client.get("/api/settings/album-path")
        assert resp.status_code == 200
        assert resp.json.get("album_path") in (None, "")

    def test_set_album_path(self, client, tmp_path):
        """PUT 设置相册路径"""
        target = tmp_path / "new_album"
        target.mkdir()
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.set_album_path_only.return_value = True
            mock_gcm.return_value = mock_cfg
            resp = client.put(
                "/api/settings/album-path",
                json={"album_path": str(target)},
            )
        # 200（成功）或 202（异步启动）都合理
        assert resp.status_code in (200, 202)
        body = resp.json
        assert "status" in body
        assert "album_path" in body

    def test_set_album_path_missing(self, client):
        """缺 album_path 字段应返回 400"""
        resp = client.put("/api/settings/album-path", json={})
        assert resp.status_code == 400

    def test_set_album_path_nonexistent(self, client, tmp_path):
        """不存在的路径应返回 404"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_gcm.return_value = MagicMock()
            resp = client.put(
                "/api/settings/album-path",
                json={"album_path": str(tmp_path / "nope")},
            )
        assert resp.status_code == 404


class TestLanguageEndpoint:
    """GET / PUT /api/settings/language"""

    def test_get_language_default(self, client):
        """获取语言偏好（未设置时）"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_setting.return_value = None
            mock_gcm.return_value = mock_cfg
            resp = client.get("/api/settings/language")
        assert resp.status_code == 200
        assert "language" in resp.json

    def test_set_language_zh(self, client):
        """设置中文"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_gcm.return_value = mock_cfg
            resp = client.put("/api/settings/language", json={"language": "zh"})
        assert resp.status_code == 200
        assert resp.json["status"] == "ok"
        assert resp.json["language"] == "zh"

    def test_set_language_en(self, client):
        """设置英文"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_gcm.return_value = mock_cfg
            resp = client.put("/api/settings/language", json={"language": "en"})
        assert resp.status_code == 200
        assert resp.json["language"] == "en"

    def test_set_language_invalid(self, client):
        """无效语言代码应返回 400"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_gcm.return_value = MagicMock()
            resp = client.put("/api/settings/language", json={"language": "fr"})
        assert resp.status_code == 400


class TestThemeEndpoint:
    """GET / PUT /api/settings/theme"""

    def test_get_theme_default(self, client):
        """获取主题偏好（默认 system）"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_setting.return_value = "system"
            mock_gcm.return_value = mock_cfg
            resp = client.get("/api/settings/theme")
        assert resp.status_code == 200
        assert resp.json["theme"] == "system"

    def test_set_theme_light(self, client):
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_gcm.return_value = MagicMock()
            resp = client.put("/api/settings/theme", json={"theme": "light"})
        assert resp.status_code == 200
        assert resp.json["theme"] == "light"

    def test_set_theme_dark(self, client):
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_gcm.return_value = MagicMock()
            resp = client.put("/api/settings/theme", json={"theme": "dark"})
        assert resp.status_code == 200
        assert resp.json["theme"] == "dark"

    def test_set_theme_invalid(self, client):
        """无效主题应返回 400"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_gcm.return_value = MagicMock()
            resp = client.put("/api/settings/theme", json={"theme": "neon"})
        assert resp.status_code == 400


class TestSystemLocaleEndpoint:
    """GET /api/system/locale"""

    def test_get_system_locale(self, client):
        """获取系统 locale"""
        resp = client.get("/api/system/locale")
        assert resp.status_code == 200
        body = resp.json
        assert "language" in body
        assert body["language"] in ("zh", "en")


class TestRebuildIndexEndpoint:
    """POST /api/settings/rebuild-index"""

    def test_rebuild_index_no_album(self, client):
        """未设置相册路径时返回 400"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = None
            mock_gcm.return_value = mock_cfg
            resp = client.post("/api/settings/rebuild-index")
        assert resp.status_code == 400

    def test_rebuild_index_success(self, client, tmp_path):
        """成功启动重建任务"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(tmp_path)
            mock_gcm.return_value = mock_cfg
            with patch("backend.api_server.get_thumbnail_manager") as mock_gtm:
                mock_tm = MagicMock()
                mock_tm.cache_dir = tmp_path / "cache"
                mock_gtm.return_value = mock_tm
                resp = client.post("/api/settings/rebuild-index")
        assert resp.status_code == 200
        body = resp.json
        assert "task_id" in body

    def test_rebuild_progress_unknown_id(self, client):
        """未知 task_id 返回 404"""
        resp = client.get("/api/settings/rebuild-progress/rebuild_does_not_exist")
        assert resp.status_code == 404
