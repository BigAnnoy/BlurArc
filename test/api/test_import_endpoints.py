"""
/api/import/* 端点测试

实际 api_server.py 实现：
- POST /api/import/check        (同步，body: source_path)
- POST /api/import/check/start  (异步，返回 check_id)
- GET  /api/import/check/progress/<check_id>
- POST /api/import/start        (body: source_path, target_path, import_mode)
- GET  /api/import/progress/<import_id>
- POST /api/import/cancel/<import_id>
- POST /api/import/pause/<import_id>
- POST /api/import/resume/<import_id>

注意：plan 中的字段名是 source / target，实际实现是 source_path / target_path。
"""
from pathlib import Path
import time
import pytest


class TestImportCheckEndpoint:
    """POST /api/import/check（同步）"""

    def test_check_directory(self, client, sample_album):
        """正常导入预检"""
        resp = client.post(
            "/api/import/check",
            json={"source_path": str(sample_album)},
        )
        assert resp.status_code == 200
        data = resp.json
        # 实际返回字段：status, source_path, media_count, total_size, total_size_mb,
        #                preview, date_folders, target_duplicates, source_duplicates
        assert "status" in data
        assert "media_count" in data or "total_files" in data
        # 10 张测试图（sample_album fixture）
        if "media_count" in data:
            assert data["media_count"] == 10
        elif "total_files" in data:
            assert data["total_files"] == 10

    def test_check_nonexistent_directory(self, client, tmp_path):
        """不存在的源目录应返回 404"""
        resp = client.post(
            "/api/import/check",
            json={"source_path": str(tmp_path / "nope")},
        )
        assert resp.status_code == 404

    def test_check_not_a_directory(self, client, tmp_path):
        """不是目录应返回 400"""
        f = tmp_path / "not_a_dir.txt"
        f.write_text("x")
        resp = client.post(
            "/api/import/check",
            json={"source_path": str(f)},
        )
        assert resp.status_code == 400

    def test_check_missing_source_path(self, client):
        """缺 source_path 字段应返回 400"""
        resp = client.post("/api/import/check", json={})
        assert resp.status_code == 400


class TestImportCheckStartAsyncEndpoint:
    """POST /api/import/check/start（异步）"""

    def test_start_async(self, client, sample_album):
        """异步检查应返回 check_id"""
        resp = client.post(
            "/api/import/check/start",
            json={"source_path": str(sample_album)},
        )
        assert resp.status_code == 200
        body = resp.json
        assert body.get("status") == "started"
        assert "check_id" in body

    def test_async_progress(self, client, sample_album):
        """异步检查 + 查询进度"""
        # 启动
        resp = client.post(
            "/api/import/check/start",
            json={"source_path": str(sample_album)},
        )
        check_id = resp.json["check_id"]

        # 轮询进度（最多 10 秒）
        final = None
        for _ in range(20):
            pr = client.get(f"/api/import/check/progress/{check_id}")
            assert pr.status_code == 200
            body = pr.json
            if body.get("status") in ("completed", "failed"):
                final = body
                break
            time.sleep(0.5)

        assert final is not None, "async check never finished"
        assert final["status"] == "completed"

    def test_async_progress_unknown_id(self, client):
        """未知 check_id 应返回 404"""
        resp = client.get("/api/import/check/progress/check_does_not_exist")
        assert resp.status_code == 404

    def test_async_missing_source_path(self, client):
        """缺 source_path 字段应返回 400"""
        resp = client.post("/api/import/check/start", json={})
        assert resp.status_code == 400


class TestImportStartEndpoint:
    """POST /api/import/start"""

    def test_start_import(self, client, sample_album, tmp_path):
        """启动导入任务"""
        target = tmp_path / "target"
        target.mkdir()
        resp = client.post(
            "/api/import/start",
            json={
                "source_path": str(sample_album),
                "target_path": str(target),
            },
        )
        assert resp.status_code == 200
        body = resp.json
        assert body.get("status") == "started"
        assert "import_id" in body
        assert "message" in body

    def test_start_import_missing_source(self, client, tmp_path):
        """缺 source_path 应返回 400"""
        target = tmp_path / "target"
        target.mkdir()
        resp = client.post(
            "/api/import/start",
            json={"target_path": str(target)},
        )
        assert resp.status_code == 400

    def test_start_import_nonexistent_source(self, client, tmp_path):
        """不存在的源目录应返回 400"""
        target = tmp_path / "target"
        target.mkdir()
        resp = client.post(
            "/api/import/start",
            json={
                "source_path": str(tmp_path / "nope"),
                "target_path": str(target),
            },
        )
        assert resp.status_code == 400

    def test_start_import_nonexistent_target(self, client, sample_album, tmp_path):
        """不存在的目标目录应返回 400"""
        resp = client.post(
            "/api/import/start",
            json={
                "source_path": str(sample_album),
                "target_path": str(tmp_path / "nope_target"),
            },
        )
        assert resp.status_code == 400


class TestImportProgressEndpoint:
    """GET /api/import/progress/<import_id>"""

    def test_progress_unknown_id(self, client):
        """未知 import_id 应返回 404"""
        resp = client.get("/api/import/progress/import_does_not_exist")
        assert resp.status_code == 404

    def test_progress_after_start(self, client, sample_album, tmp_path):
        """启动后查询进度"""
        target = tmp_path / "target"
        target.mkdir()
        start = client.post(
            "/api/import/start",
            json={
                "source_path": str(sample_album),
                "target_path": str(target),
            },
        )
        import_id = start.json["import_id"]
        # 立即查询
        resp = client.get(f"/api/import/progress/{import_id}")
        assert resp.status_code == 200
        body = resp.json
        # 关键字段
        for key in ("import_id", "status", "progress", "total_files"):
            assert key in body, f"missing {key}"


class TestImportControlEndpoints:
    """POST /api/import/{cancel,pause,resume}/<import_id>"""

    def _start_import(self, client, sample_album, tmp_path):
        target = tmp_path / "target"
        target.mkdir()
        start = client.post(
            "/api/import/start",
            json={
                "source_path": str(sample_album),
                "target_path": str(target),
            },
        )
        return start.json["import_id"]

    def test_cancel_import(self, client, sample_album, tmp_path):
        import_id = self._start_import(client, sample_album, tmp_path)
        resp = client.post(f"/api/import/cancel/{import_id}")
        assert resp.status_code == 200
        body = resp.json
        assert body["status"] == "cancelled"

    def test_pause_import(self, client, sample_album, tmp_path):
        import_id = self._start_import(client, sample_album, tmp_path)
        resp = client.post(f"/api/import/pause/{import_id}")
        assert resp.status_code == 200
        body = resp.json
        assert body["status"] == "paused"

    def test_resume_import(self, client, sample_album, tmp_path):
        import_id = self._start_import(client, sample_album, tmp_path)
        # 先 pause 再 resume
        client.post(f"/api/import/pause/{import_id}")
        resp = client.post(f"/api/import/resume/{import_id}")
        assert resp.status_code == 200
        body = resp.json
        assert body["status"] == "processing"

    def test_cancel_unknown_id(self, client):
        resp = client.post("/api/import/cancel/import_does_not_exist")
        assert resp.status_code == 404

    def test_pause_unknown_id(self, client):
        resp = client.post("/api/import/pause/import_does_not_exist")
        assert resp.status_code == 404

    def test_resume_unknown_id(self, client):
        resp = client.post("/api/import/resume/import_does_not_exist")
        assert resp.status_code == 404
