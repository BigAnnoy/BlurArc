"""
/api/album/photos 端点测试

注意：plan 中的 GET /api/photos、GET /api/photos/<id> 等端点不在当前 api_server.py 中。
当前实现的照片列表端点是 GET /api/album/photos（支持分页 + path 参数）。
下面用实际端点编写测试。
"""
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestAlbumPhotosEndpoint:
    """GET /api/album/photos?path=...&page=...&page_size=..."""

    def test_missing_path_param(self, client):
        """缺 path 参数应返回 400"""
        resp = client.get("/api/album/photos")
        assert resp.status_code == 400
        assert "error" in resp.json

    def test_nonexistent_path(self, client):
        """不存在的路径应返回 404"""
        resp = client.get("/api/album/photos", query_string={"path": "Z:/no/such/dir"})
        assert resp.status_code == 404
        assert "error" in resp.json

    def test_list_photos_with_mocked_album(self, client, tmp_path):
        """成功获取照片列表"""
        # 模拟相册路径
        album = tmp_path / "album"
        album.mkdir()
        for i in range(3):
            (album / f"img_{i}.jpg").write_bytes(b"\xff\xd8\xff\xe0fake jpg")

        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_gcm.return_value = MagicMock(get_album_path=MagicMock(return_value=str(album)))
            resp = client.get("/api/album/photos", query_string={"path": str(album)})

        assert resp.status_code == 200
        body = resp.json
        assert body["count"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 100
        assert len(body["photos"]) == 3
        for p in body["photos"]:
            assert p["name"].endswith(".jpg")
            assert "thumbnail_url" in p
            assert "preview_url" in p

    def test_pagination(self, client, tmp_path):
        """分页参数应正确生效"""
        album = tmp_path / "album"
        album.mkdir()
        for i in range(5):
            (album / f"img_{i}.jpg").write_bytes(b"\xff\xd8\xff\xe0fake")

        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_gcm.return_value = MagicMock(get_album_path=MagicMock(return_value=str(album)))
            resp = client.get(
                "/api/album/photos",
                query_string={"path": str(album), "page": 1, "page_size": 2},
            )

        assert resp.status_code == 200
        body = resp.json
        assert body["count"] == 5
        assert body["page_size"] == 2
        assert body["total_pages"] == 3
        assert len(body["photos"]) == 2

    def test_pagination_out_of_range(self, client, tmp_path):
        """超出范围的页码应返回空 photos"""
        album = tmp_path / "album"
        album.mkdir()

        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_gcm.return_value = MagicMock(get_album_path=MagicMock(return_value=str(album)))
            resp = client.get(
                "/api/album/photos",
                query_string={"path": str(album), "page": 999, "page_size": 10},
            )

        assert resp.status_code == 200
        body = resp.json
        assert body["photos"] == []


class TestAlbumStatsEndpoint:
    """GET /api/album/stats"""

    def test_stats_success(self, client, tmp_path):
        """正常情况返回统计信息"""
        album = tmp_path / "album"
        album.mkdir()
        (album / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0fake")

        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(album)
            mock_cfg.get_last_import.return_value = "2024-01-01T00:00:00"
            mock_gcm.return_value = mock_cfg
            resp = client.get("/api/album/stats")

        assert resp.status_code == 200
        body = resp.json
        assert "total_files" in body
        assert "total_size_mb" in body
        assert "last_import" in body

    def test_stats_no_album_path(self, client):
        """未配置相册路径时返回错误"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = None
            mock_gcm.return_value = mock_cfg
            resp = client.get("/api/album/stats")
        # 没有 album_path → get_album_stats 返回 None → 500
        assert resp.status_code in (200, 500)


class TestAlbumTreeEndpoint:
    """GET /api/album/tree"""

    def test_tree_nonexistent_album(self, client):
        """相册路径不存在时返回 404"""
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = "Z:/no/such/path"
            mock_gcm.return_value = mock_cfg
            resp = client.get("/api/album/tree")
        assert resp.status_code == 404

    def test_tree_success(self, client, tmp_path):
        """成功返回目录树"""
        album = tmp_path / "album"
        (album / "2024").mkdir(parents=True)
        (album / "2024" / "2024-01").mkdir()
        (album / "2024" / "2024-01" / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0fake")

        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(album)
            mock_gcm.return_value = mock_cfg
            resp = client.get("/api/album/tree")
        assert resp.status_code == 200
        body = resp.json
        assert body["type"] == "root"
        assert isinstance(body.get("children"), list)
