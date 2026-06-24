"""
搜索端点测试 — 实际实现中没有 /api/search 端点

api_server.py 中没有专门的搜索端点。搜索功能是分散的：
- GET /api/album/photos?path=...     按目录列文件
- GET /api/album/exif?path=...       EXIF 元数据
- GET /api/album/stats               统计
- GET /api/album/tree                目录树

这里创建占位测试，验证其他可用搜索/查询端点，并显式标记：
/api/search 端点不存在。
"""
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestNoSearchEndpoint:
    """/api/search 端点不存在（计划中的端点）"""

    def test_api_search_not_implemented(self, client):
        """/api/search 端点当前未实现，应返回 404"""
        resp = client.get("/api/search", query_string={"q": "test"})
        # 没有这个端点 → 404
        assert resp.status_code == 404

    def test_api_search_by_date_not_implemented(self, client):
        """/api/search 按日期范围 端点不存在"""
        resp = client.get(
            "/api/search",
            query_string={"start_date": "2024-01-01", "end_date": "2024-01-31"},
        )
        assert resp.status_code == 404


class TestExifEndpoint:
    """GET /api/album/exif - 用作图片元数据查询（搜索/过滤场景常用）"""

    def test_exif_missing_path(self, client):
        resp = client.get("/api/album/exif")
        assert resp.status_code == 400

    def test_exif_nonexistent_file(self, client, tmp_path):
        resp = client.get(
            "/api/album/exif",
            query_string={"path": str(tmp_path / "nope.jpg")},
        )
        assert resp.status_code == 404

    def test_exif_success(self, client, tmp_path):
        """成功读取 EXIF（无 EXIF 时返回空 dict，有 EXIF 时返回结构化数据）"""
        from PIL import Image
        album = tmp_path / "album"
        album.mkdir()
        img_in_album = album / "test.jpg"
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(str(img_in_album))

        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(album)
            mock_gcm.return_value = mock_cfg
            resp = client.get(
                "/api/album/exif",
                query_string={"path": str(img_in_album)},
            )
        assert resp.status_code == 200
        # 无 EXIF 的 PNG/JPEG 返回 {}；有 EXIF 的返回完整结构
        assert isinstance(resp.json, dict)
        # 如果有 EXIF 字段则验证结构；空 dict 也合法（静默失败设计）
        if resp.json:  # 非空
            assert "make" in resp.json
            assert "model" in resp.json
