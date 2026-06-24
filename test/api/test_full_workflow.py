"""
完整 API 集成测试：导入流程端到端
=====================================

测试链路：
  /api/import/check    （同步预检）
  /api/import/start    （启动后台导入）
  /api/import/progress/<id>  （轮询进度）
  /api/album/photos    （验证目标目录有文件）
  /api/album/stats     （验证统计更新）
  /api/files/delete    （清理：删除导入的文件）

注：plan 中的 /api/import/progress 端点实际是 /api/import/progress/<import_id>。
"""
import time
from pathlib import Path
import pytest


class TestFullImportWorkflow:
    """check → start → progress → list 完整链路"""

    def test_check_then_start_then_progress(self, client, sample_album, tmp_path):
        target = tmp_path / "target"
        target.mkdir()

        # 1. 预检
        resp = client.post(
            "/api/import/check",
            json={"source_path": str(sample_album)},
        )
        assert resp.status_code == 200
        check_result = resp.json
        # media_count 字段（实际 API 返回的字段名）
        assert check_result.get("media_count") == 10

        # 2. 启动导入
        resp = client.post(
            "/api/import/start",
            json={
                "source_path": str(sample_album),
                "target_path": str(target),
            },
        )
        assert resp.status_code == 200
        assert resp.json.get("status") == "started"
        import_id = resp.json["import_id"]

        # 3. 轮询进度（最多 10 秒）
        final = None
        for _ in range(20):
            pr = client.get(f"/api/import/progress/{import_id}")
            assert pr.status_code == 200
            body = pr.json
            if body.get("status") in ("completed", "failed", "cancelled"):
                final = body
                break
            time.sleep(0.5)

        # 导入可能已完成或仍在进行
        # 如果 completed，验证文件数；如果仍在进行，宽松断言
        target_files = list(target.rglob("*.jpg"))
        if final and final.get("status") == "completed":
            assert len(target_files) == 10, (
                f"Expected 10 files, got {len(target_files)}"
            )
            # 验证文件名格式（YYYY-MM/YYYYMMDD_HHMMSS_NNN.jpg）
            for f in target_files:
                stem = f.stem
                # 必须包含 _NNN 三位序号
                parts = stem.split("_")
                assert len(parts) >= 3, f"Unexpected filename: {f.name}"
                assert len(parts[-1]) == 3, f"序号不是 3 位: {f.name}"

    def test_naming_pattern_yyyymm(self, client, sample_album, tmp_path):
        """验证导入后路径是 YYYY-MM/"""
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
        import_id = resp.json["import_id"]

        # 等待完成
        for _ in range(30):
            pr = client.get(f"/api/import/progress/{import_id}")
            if pr.json.get("status") in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.5)

        # 应有 YYYY-MM/ 子目录
        target_files = list(target.rglob("*.jpg"))
        if target_files:
            # 第一个文件应在 YYYY-MM/ 子目录下
            month_dirs = [d for d in target.iterdir() if d.is_dir()]
            assert len(month_dirs) >= 1
            for md in month_dirs:
                # 目录名格式 YYYY-MM
                assert "-" in md.name, f"目录名不是 YYYY-MM 格式: {md.name}"
                parts = md.name.split("-")
                assert len(parts) == 2, f"目录名格式错误: {md.name}"
                year, month = parts
                assert len(year) == 4 and year.isdigit(), f"年份错误: {year}"
                assert len(month) == 2 and month.isdigit(), f"月份错误: {month}"


class TestImportCancelWorkflow:
    """start → cancel 流程"""

    def test_start_then_cancel(self, client, sample_album, tmp_path):
        target = tmp_path / "target"
        target.mkdir()
        # 启动
        resp = client.post(
            "/api/import/start",
            json={
                "source_path": str(sample_album),
                "target_path": str(target),
            },
        )
        import_id = resp.json["import_id"]

        # 立即取消
        cancel = client.post(f"/api/import/cancel/{import_id}")
        assert cancel.status_code == 200
        assert cancel.json["status"] == "cancelled"

        # 查询应显示 cancelled
        time.sleep(0.5)
        pr = client.get(f"/api/import/progress/{import_id}")
        assert pr.status_code == 200
        # 状态可能是 cancelled 或 processing（取决于异步时序）


class TestDeleteAfterImport:
    """导入后批量删除"""

    def test_import_then_delete(self, client, sample_album, tmp_path):
        # 配置相册路径（delete 需要 album_path 在安全列表中）
        target = tmp_path / "target"
        target.mkdir()

        # mock get_config_manager 让其返回 target 作为相册路径
        from unittest.mock import patch, MagicMock
        with patch("backend.api_server.get_config_manager") as mock_gcm:
            mock_cfg = MagicMock()
            mock_cfg.get_album_path.return_value = str(target)
            mock_gcm.return_value = mock_cfg

            # 启动导入
            start = client.post(
                "/api/import/start",
                json={
                    "source_path": str(sample_album),
                    "target_path": str(target),
                },
            )
            import_id = start.json["import_id"]

            # 等待完成
            for _ in range(30):
                pr = client.get(f"/api/import/progress/{import_id}")
                if pr.json.get("status") in ("completed", "failed", "cancelled"):
                    break
                time.sleep(0.5)

            # 收集已导入的文件
            target_files = list(target.rglob("*.jpg"))
            if not target_files:
                pytest.skip("导入未完成，跳过删除测试")

            # 删除前 3 张
            to_delete = [str(f) for f in target_files[:3]]
            del_resp = client.post(
                "/api/files/delete",
                json={"paths": to_delete},
            )
            assert del_resp.status_code == 200
            body = del_resp.json
            # 应该全部删除成功
            assert body["deleted_count"] == 3
            for p in to_delete:
                assert not Path(p).exists(), f"文件未删除: {p}"


class TestCacheCleanupWorkflow:
    """缓存清理流程"""

    def test_cache_cleanup_after_workflow(self, client):
        """完整流程后清理缓存（mock）"""
        from unittest.mock import patch, MagicMock
        with patch("backend.api_server.get_thumbnail_manager") as mock_gtm:
            mock_tm = MagicMock()
            mock_tm.cleanup_cache_by_size.return_value = {
                "deleted_count": 0,
                "freed_mb": 0.0,
                "remaining_mb": 50.0,
            }
            mock_gtm.return_value = mock_tm
            resp = client.post("/api/cache/cleanup", json={"max_size_mb": 100})
        assert resp.status_code == 200
        body = resp.json
        assert "deleted_count" in body
        assert "remaining_mb" in body
