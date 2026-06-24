"""
/api/files/* 端点测试

实际 api_server.py 实现：
- POST /api/files/delete - 删除文件（受相册目录 + 源文件夹安全检查）
- 注：plan 中的 GET /api/files、GET /api/photos 等端点在当前实现中不存在，
  这些用例改用 mock 替代或用实际存在的端点（/api/album/photos）覆盖。
"""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


class TestFilesDeleteEndpoint:
    """POST /api/files/delete"""

    def test_delete_empty_list(self, client):
        """空路径列表应返回 400"""
        resp = client.post("/api/files/delete", json={"paths": []})
        assert resp.status_code == 400
        assert "error" in resp.json

    def test_delete_missing_paths_key(self, client):
        """缺少 paths 字段应返回 400"""
        resp = client.post("/api/files/delete", json={})
        assert resp.status_code == 400

    def test_delete_paths_not_list(self, client):
        """paths 不是 list 应返回 400"""
        resp = client.post("/api/files/delete", json={"paths": "not a list"})
        assert resp.status_code == 400

    def test_delete_files_outside_allowed_dirs(self, client, tmp_path):
        """相册目录外、源文件夹外的文件应被拒绝"""
        # 不在配置相册中，也不在 source_paths 中 → 拒绝
        outside = tmp_path / "outside.jpg"
        outside.write_text("x")
        resp = client.post(
            "/api/files/delete",
            json={"paths": [str(outside)]},
        )
        # 所有路径都被拒绝，deleted_count 为 0
        assert resp.status_code == 200
        body = resp.json
        assert body["deleted_count"] == 0
        assert len(body["failed"]) >= 1
        assert outside.exists()  # 文件应仍存在

    def test_delete_nonexistent_file(self, client, tmp_path):
        """不存在的文件应被记录到 failed"""
        nonexistent = tmp_path / "nope.jpg"
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_gcm.return_value = MagicMock(get_album_path=MagicMock(return_value=str(tmp_path)))
            resp = client.post(
                "/api/files/delete",
                json={"paths": [str(nonexistent)]},
            )
        assert resp.status_code == 200
        body = resp.json
        assert body["deleted_count"] == 0
        assert len(body["failed"]) >= 1


class TestFilesDeleteSecurity:
    """安全测试：路径遍历攻击防护"""

    def test_reject_path_traversal(self, client, tmp_path):
        """试图通过 ../ 访问相册外的文件应被拒绝"""
        # 尝试删除一个 .. 路径
        traversal_path = str(tmp_path / ".." / ".." / "etc" / "passwd")
        resp = client.post(
            "/api/files/delete",
            json={"paths": [traversal_path]},
        )
        # 应返回 200（不是 404/400），但 deleted_count=0，failed 中有记录
        assert resp.status_code == 200
        body = resp.json
        assert body["deleted_count"] == 0
