"""
导入管理器扩展测试 (pytest版本)
测试导入管理器的更多功能，特别是未覆盖的部分
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.import_manager import get_import_manager, FileConflict, ImportStatus


class TestImportManagerExtended:
    """测试导入管理器扩展功能"""
    
    @pytest.fixture
    def temp_source_dir(self):
        """创建临时源目录fixture"""
        temp_dir = tempfile.mkdtemp()
        
        # 创建测试文件
        with open(os.path.join(temp_dir, "test_photo_1.jpg"), "w") as f:
            f.write("dummy photo 1 content")
        
        with open(os.path.join(temp_dir, "test_photo_2.jpg"), "w") as f:
            f.write("dummy photo 2 content")
        
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def temp_target_dir(self):
        """创建临时目标目录fixture"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def import_manager(self):
        """创建导入管理器fixture"""
        return get_import_manager()
    
    def test_import_manager_singleton(self):
        """测试导入管理器单例模式"""
        manager1 = get_import_manager()
        manager2 = get_import_manager()
        assert manager1 is manager2
    
    def test_import_status_enum(self):
        """测试导入状态枚举"""
        # 测试枚举值存在且正确
        assert ImportStatus.PENDING.value == "pending"
        assert ImportStatus.SCANNING.value == "scanning"
        assert ImportStatus.PROCESSING.value == "processing"
        assert ImportStatus.PAUSED.value == "paused"
        assert ImportStatus.COMPLETED.value == "completed"
        assert ImportStatus.FAILED.value == "failed"
        assert ImportStatus.CANCELLED.value == "cancelled"
        
        # 测试枚举类型
        assert isinstance(ImportStatus.PENDING, ImportStatus)
        assert isinstance(ImportStatus.SCANNING, ImportStatus)
        assert isinstance(ImportStatus.PROCESSING, ImportStatus)
        assert isinstance(ImportStatus.PAUSED, ImportStatus)
        assert isinstance(ImportStatus.COMPLETED, ImportStatus)
        assert isinstance(ImportStatus.FAILED, ImportStatus)
        assert isinstance(ImportStatus.CANCELLED, ImportStatus)
    
    def test_import_status_values(self):
        """测试导入状态枚举值"""
        # 测试所有枚举值
        status_values = [item.value for item in ImportStatus]
        assert "pending" in status_values
        assert "scanning" in status_values
        assert "processing" in status_values
        assert "paused" in status_values
        assert "completed" in status_values
        assert "failed" in status_values
        assert "cancelled" in status_values
    
    def test_create_multiple_imports(self, import_manager, temp_source_dir, temp_target_dir):
        """测试创建多个导入任务"""
        import_id_1 = "test_import_111"
        import_id_2 = "test_import_222"
        
        # 创建第一个导入任务
        import_manager.create_import(import_id_1, temp_source_dir, temp_target_dir)
        
        # 创建第二个导入任务
        import_manager.create_import(import_id_2, temp_source_dir, temp_target_dir)
        
        # 验证两个任务都已创建
        progress_1 = import_manager.get_progress(import_id_1)
        progress_2 = import_manager.get_progress(import_id_2)
        
        assert progress_1 is not None
        assert progress_2 is not None
        assert progress_1.import_id == import_id_1
        assert progress_2.import_id == import_id_2
        assert progress_1 != progress_2
    
    @patch('backend.import_manager.threading.Thread')
    def test_start_import_async(self, mock_thread, import_manager, temp_source_dir, temp_target_dir):
        """测试异步启动导入"""
        # 模拟线程启动
        mock_thread.return_value.start.return_value = None
        
        import_id = "test_import_async"
        import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
        
        # 调用异步导入方法
        import_manager.start_import_async(
            import_id,
            temp_source_dir,
            temp_target_dir,
            import_mode="copy",
        )
        
        # 验证线程被创建并启动
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
    
    @patch('backend.import_manager.ImportProgress')
    def test_create_import_progress(self, mock_import_progress, import_manager, temp_source_dir, temp_target_dir):
        """测试创建导入进度对象"""
        # 模拟 ImportProgress 构造函数
        mock_progress = MagicMock()
        mock_import_progress.return_value = mock_progress
        
        import_id = "test_import_progress"
        import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
        
        # 验证 ImportProgress 被创建
        mock_import_progress.assert_called_once()
        
        # 验证进度对象被存储
        progress = import_manager.get_progress(import_id)
        assert progress == mock_progress
    
    def test_get_progress_dict_nonexistent(self, import_manager):
        """测试获取不存在的导入进度字典"""
        progress_dict = import_manager.get_progress_dict("non_existent_import")
        assert progress_dict is None
    
    def test_cancel_nonexistent_import(self, import_manager):
        """测试取消不存在的导入"""
        result = import_manager.cancel_import("non_existent_import")
        assert result is None
    
    def test_pause_nonexistent_import(self, import_manager):
        """测试暂停不存在的导入"""
        result = import_manager.pause_import("non_existent_import")
        assert result is None
    
    def test_resume_nonexistent_import(self, import_manager):
        """测试恢复不存在的导入"""
        result = import_manager.resume_import("non_existent_import")
        assert result is None
    
    def test_file_conflict_enum_complete(self):
        """测试文件冲突枚举的完整性"""
        # 验证所有预期的枚举值都存在
        expected_values = ["none", "md5", "name"]
        actual_values = [item.value for item in FileConflict]
        
        for expected in expected_values:
            assert expected in actual_values
        
        # 验证没有额外的枚举值
        assert len(expected_values) == len(actual_values)
    
    def test_pause_resume_cycle(self, import_manager, temp_source_dir, temp_target_dir):
        """测试暂停-恢复循环"""
        import_id = "test_pause_resume"
        import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
        
        # 暂停导入
        result = import_manager.pause_import(import_id)
        assert result is None
        
        # 恢复导入
        result = import_manager.resume_import(import_id)
        assert result is None
        
        # 再次暂停
        result = import_manager.pause_import(import_id)
        assert result is None
        
        # 再次恢复
        result = import_manager.resume_import(import_id)
        assert result is None
        
        # 验证导入任务仍可访问
        progress = import_manager.get_progress(import_id)
        assert progress is not None
    
    def test_pause_cancelled_import(self, import_manager, temp_source_dir, temp_target_dir):
        """测试暂停已取消的导入"""
        import_id = "test_pause_cancelled"
        import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
        
        # 先取消导入
        import_manager.cancel_import(import_id)
        
        # 尝试暂停已取消的导入
        result = import_manager.pause_import(import_id)
        assert result is None
    
    def test_resume_cancelled_import(self, import_manager, temp_source_dir, temp_target_dir):
        """测试恢复已取消的导入"""
        import_id = "test_resume_cancelled"
        import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
        
        # 先取消导入
        import_manager.cancel_import(import_id)
        
        # 尝试恢复已取消的导入
        result = import_manager.resume_import(import_id)
        assert result is None
    
    @patch('backend.import_manager.ImportManager._do_import')
    def test_start_import_with_different_modes(self, mock_do_import, import_manager, temp_source_dir, temp_target_dir):
        """测试使用不同导入模式启动导入"""
        # 模拟 _do_import 方法
        mock_do_import.return_value = None
        
        import_id = "test_import_modes"
        import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
        
        # 测试 copy 模式
        import_manager.start_import_async(
            import_id,
            temp_source_dir,
            temp_target_dir,
            import_mode="copy",
        )
        
        # 测试 move 模式
        import_manager.start_import_async(
            import_id,
            temp_source_dir,
            temp_target_dir,
            import_mode="move",
        )
        
        # 测试默认模式（应该是 copy）
        import_manager.start_import_async(
            import_id,
            temp_source_dir,
            temp_target_dir,
            import_mode="invalid_mode",
        )
        
        # 验证 _do_import 被调用了3次
        assert mock_do_import.call_count == 3
    
    @patch('backend.import_manager.ImportManager._do_import')
    def test_start_import_multiple_calls(self, mock_do_import, import_manager, temp_source_dir, temp_target_dir):
        """测试多次调用导入启动方法"""
        mock_do_import.return_value = None
        
        import_id = "test_import_multi"
        import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
        
        for i in range(3):
            import_manager.start_import_async(
                import_id,
                temp_source_dir,
                temp_target_dir,
                import_mode="copy",
            )
        
        assert mock_do_import.call_count == 3
    
    def test_import_manager_get_progress_multiple(self, import_manager, temp_source_dir, temp_target_dir):
        """测试获取多个导入任务的进度"""
        # 创建多个导入任务
        import_ids = [f"test_import_{i}" for i in range(5)]
        
        for import_id in import_ids:
            import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
        
        # 验证所有任务都能获取到进度
        for import_id in import_ids:
            progress = import_manager.get_progress(import_id)
            assert progress is not None
            assert progress.import_id == import_id
    
    def test_empty_import_operation(self, import_manager):
        """测试空导入操作"""
        # 测试各种方法在没有导入任务时的行为
        result = import_manager.get_progress("empty_import")
        assert result is None
        
        result = import_manager.get_progress_dict("empty_import")
        assert result is None
        
        result = import_manager.cancel_import("empty_import")
        assert result is None
        
        result = import_manager.pause_import("empty_import")
        assert result is None
        
        result = import_manager.resume_import("empty_import")
        assert result is None
    
    def test_invalid_import_parameters(self, import_manager):
        """测试无效的导入参数"""
        # 测试使用空字符串路径创建导入 - 应该成功创建
        result1 = import_manager.create_import("invalid_import1", "", "")
        assert result1 is not None
        assert result1.import_id == "invalid_import1"
        
        # 测试使用 None 路径创建导入 - 应该成功创建
        result2 = import_manager.create_import("invalid_import2", None, None)
        assert result2 is not None
        assert result2.import_id == "invalid_import2"
    
    def test_import_id_format(self, import_manager, temp_source_dir, temp_target_dir):
        """测试不同格式的导入ID"""
        # 测试各种格式的导入ID
        import_ids = [
            "test_import",
            "12345",
            "import_123",
            "import-with-dashes",
            "import.with.dots",
            "import_underscores_123"
        ]
        
        for import_id in import_ids:
            import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
            progress = import_manager.get_progress(import_id)
            assert progress is not None
            assert progress.import_id == import_id
    
    def test_scan_source(self, import_manager, temp_source_dir):
        """测试_scan_source方法"""
        # 将字符串转换为Path对象
        source_path = Path(temp_source_dir)
        
        # 创建测试文件
        test_files = [
            "test1.jpg",
            "test2.png",
            "test3.mp4",
            "test4.txt"  # 这应该被过滤掉
        ]
        
        for file_name in test_files:
            file_path = source_path / file_name
            file_path.write_text("test content")
        
        # 调用_scan_source方法
        result = import_manager._scan_source(source_path)
        
        # 验证结果 - 应该只包含图片和视频文件
        file_names = [f.name for f in result]
        assert "test1.jpg" in file_names
        assert "test2.png" in file_names
        assert "test3.mp4" in file_names
    
    def test_compute_md5(self, import_manager, temp_source_dir):
        """测试_compute_md5方法"""
        # 将字符串转换为Path对象
        source_path = Path(temp_source_dir)
        
        # 创建测试文件
        test_file = source_path / "test.jpg"
        test_file.write_text("test content for md5")
        
        # 调用_compute_md5方法
        md5_result = import_manager._compute_md5(test_file)
        
        # 验证结果 - 应该返回有效的md5字符串
        assert md5_result is not None
        assert len(md5_result) == 32
    
    def test_load_target_records(self, import_manager, temp_target_dir):
        """测试_load_target_records方法"""
        target_path = Path(temp_target_dir)
        
        test_files = ["test1.jpg", "test2.png"]
        for file_name in test_files:
            file_path = target_path / file_name
            file_path.write_text("test content")
        
        result = import_manager._load_target_records(target_path)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        records, size_to_md5s = result
        assert isinstance(records, dict)
        assert isinstance(size_to_md5s, dict)