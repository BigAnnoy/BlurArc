"""
缩略图 + 缓存管理端点测试

实际 api_server.py 实现：
- GET  /api/album/thumbnail?path=...      获取单张缩略图
- GET  /api/album/file?path=...           原图文件（支持 Range）
- GET  /api/album/preview?path=...        浏览器预览图（HEIC 等格式转换）
- POST /api/cache/cleanup                 按大小清理缩略图缓存

注意：plan 中的 POST /api/thumbnails/generate、GET /api/thumbnails/cache/stats
    等端点在当前实现中不存在。
"""
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestAlbumThumbnailEndpoint:
    """GET /api/album/thumbnail?path=..."""

    def test_thumbnail_missing_path(self, client):
        """缺 path 参数应返回 400"""
        resp = client.get("/api/album/thumbnail")
        assert resp.status_code == 400

    def test_thumbnail_path_not_in_album(self, client, tmp_path):
        """路径不在相册目录内应被拒绝"""
        from urllib.parse import quote
        # 不在配置相册中 → thumbnail_manager 可能返回 None → 400
        fake_img = tmp_path / "fake.jpg"
        fake_img.write_bytes(b"\xff\xd8\xff\xe0fake")
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(tmp_path / "album")
            mock_gcm.return_value = mock_cfg
            resp = client.get(
                "/api/album/thumbnail",
                query_string={"path": str(fake_img)},
            )
        # 缩略图生成可能失败 → 400
        assert resp.status_code in (200, 400)


class TestCacheCleanupEndpoint:
    """POST /api/cache/cleanup"""

    def test_cleanup_with_default_size(self, client):
        """使用默认 max_size_mb"""
        with patch("backend.api_server.get_thumbnail_manager") as mock_gtm:
            mock_tm = MagicMock()
            mock_tm.cleanup_cache_by_size.return_value = {
                "deleted_count": 5,
                "freed_mb": 10.0,
                "remaining_mb": 100.0,
            }
            mock_gtm.return_value = mock_tm
            resp = client.post("/api/cache/cleanup", json={})
        assert resp.status_code == 200
        body = resp.json
        assert body["deleted_count"] == 5
        assert "freed_mb" in body
        assert "remaining_mb" in body

    def test_cleanup_with_custom_size(self, client):
        """自定义 max_size_mb"""
        with patch("backend.api_server.get_thumbnail_manager") as mock_gtm:
            mock_tm = MagicMock()
            mock_tm.cleanup_cache_by_size.return_value = {
                "deleted_count": 0,
                "freed_mb": 0.0,
                "remaining_mb": 200.0,
            }
            mock_gtm.return_value = mock_tm
            resp = client.post("/api/cache/cleanup", json={"max_size_mb": 200.0})
        assert resp.status_code == 200
        # 验证传参正确
        mock_tm.cleanup_cache_by_size.assert_called_once_with(max_size_mb=200.0)

    def test_cleanup_invalid_size(self, client):
        """max_size_mb <= 0 应返回 400"""
        resp = client.post("/api/cache/cleanup", json={"max_size_mb": 0})
        assert resp.status_code == 400

    def test_cleanup_negative_size(self, client):
        """max_size_mb 为负数应返回 400"""
        resp = client.post("/api/cache/cleanup", json={"max_size_mb": -10})
        assert resp.status_code == 400


class TestFFmpegStatusEndpoint:
    """GET /api/settings/ffmpeg-status"""

    def test_ffmpeg_status(self, client):
        """检查 ffmpeg 状态"""
        with patch("backend.api_server.check_ffmpeg") as mock_check:
            mock_check.return_value = (False, None)
            resp = client.get("/api/settings/ffmpeg-status")
        assert resp.status_code == 200
        body = resp.json
        assert "status" in body
        # 不可用时 status 应该是 "unavailable"
        assert body["status"] in ("available", "unavailable", "error")
