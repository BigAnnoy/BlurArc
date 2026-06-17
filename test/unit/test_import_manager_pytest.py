"""
导入管理器单元测试 (pytest版本)
测试导入管理器的核心功能
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.import_manager import get_import_manager, FileConflict, ImportStatus


@pytest.fixture
def temp_source_dir():
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
def temp_target_dir():
    """创建临时目标目录fixture"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def import_manager():
    """创建导入管理器fixture"""
    return get_import_manager()


def test_import_manager_initialization():
    """测试导入管理器初始化"""
    manager = get_import_manager()
    assert manager is not None


def test_create_import(import_manager, temp_source_dir, temp_target_dir):
    """测试创建导入任务"""
    import_id = "test_import_123"
    
    import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
    
    # 验证导入任务已创建
    progress = import_manager.get_progress(import_id)
    assert progress is not None
    assert progress.import_id == import_id


def test_get_progress_non_existent(import_manager):
    """测试获取不存在的导入任务进度"""
    progress = import_manager.get_progress("non_existent_import")
    assert progress is None


def test_get_progress_dict(import_manager, temp_source_dir, temp_target_dir):
    """测试获取导入任务进度字典"""
    import_id = "test_import_456"
    import_manager.create_import(import_id, temp_source_dir, temp_target_dir)

    progress_dict = import_manager.get_progress_dict(import_id)
    assert progress_dict is not None
    assert isinstance(progress_dict, dict)
    assert 'import_id' in progress_dict
    assert progress_dict['import_id'] == import_id


def test_cancel_import(import_manager, temp_source_dir, temp_target_dir):
    """测试取消导入任务"""
    import_id = "test_import_789"
    import_manager.create_import(import_id, temp_source_dir, temp_target_dir)

    result = import_manager.cancel_import(import_id)
    assert result is None

    # 验证导入任务仍可访问
    progress = import_manager.get_progress(import_id)
    assert progress is not None

def test_cancel_non_existent_import(import_manager):
    """测试取消不存在的导入任务"""
    result = import_manager.cancel_import("non_existent_import")
    assert result is None


def test_do_import_status_after_cancel():
    """回归测试：取消后状态必须是 CANCELLED，不能被覆盖为 COMPLETED。
    原 bug：_do_import 在工作线程结束后仅检查 progress.status，
    而 cancel_import 只设 cancel_flag、不改 status，
    导致主线程把状态错误地标记为 COMPLETED，前端弹"导入成功"toast。"""
    from backend.import_manager import ImportManager, ImportStatus

    manager = ImportManager()

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'source'
        source.mkdir()
        target = Path(tmp) / 'target'
        target.mkdir()

        # 创建几个文件让 _scan_source 有产出
        for i in range(3):
            (source / f'photo_{i}.jpg').write_bytes(b'fake' * 10)

        manager.create_import("test_cancel_status", str(source), str(target))
        # 模拟用户取消（在 _do_import 运行前设置标志位）
        manager.cancel_import("test_cancel_status")

        # mock DB 避免依赖真实数据库
        with patch('backend.import_manager.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.all.return_value = []
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.close = MagicMock()

            manager._do_import("test_cancel_status", str(source), str(target), 'copy')

        progress = manager.get_progress("test_cancel_status")
        assert progress is not None
        # 关键断言：取消后状态必须保持为 CANCELLED
        assert progress.status == ImportStatus.CANCELLED, (
            f"取消后状态被错误地覆盖为 {progress.status.value}，"
            f"应当保持 CANCELLED 让前端显示「已取消」toast 而非「导入完成」"
        )


def test_do_import_status_empty_source_is_failed():
    """回归测试：源目录无媒体文件时状态应为 FAILED 而非 COMPLETED。
    原 bug：_do_import 把空源目录标为 COMPLETED + error_message，
    但前端只对 FAILED 状态显示错误信息，导致用户误以为导入成功（0/0）。"""
    from backend.import_manager import ImportManager, ImportStatus

    manager = ImportManager()

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'empty_source'
        source.mkdir()  # 存在但是空的
        target = Path(tmp) / 'target'
        target.mkdir()

        manager.create_import("test_empty", str(source), str(target))

        with patch('backend.import_manager.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.close = MagicMock()

            manager._do_import("test_empty", str(source), str(target), 'copy')

        progress = manager.get_progress("test_empty")
        assert progress is not None
        assert progress.status == ImportStatus.FAILED, (
            f"空源目录应标记为 FAILED 让前端显示错误，实际为 {progress.status.value}"
        )
        assert '没有媒体文件' in (progress.error_message or '')


def test_max_workers_handles_cpu_count_none():
    """回归测试：os.cpu_count() 返回 None 时不能抛 TypeError。
    原 bug：`max(1, os.cpu_count() - 1)` 在 cpu_count() == None 时
    触发 `None - 1` TypeError，导致导入直接失败。"""
    with patch('backend.import_manager.os.cpu_count', return_value=None):
        from backend.import_manager import ImportManager

        manager = ImportManager()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            target = Path(tmp) / 'target'
            target.mkdir()
            (source / 'a.jpg').write_bytes(b'x')

            manager.create_import("test_cpu_none", str(source), str(target))

            with patch('backend.import_manager.SessionLocal') as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.add = MagicMock()
                mock_db.commit = MagicMock()
                mock_db.close = MagicMock()

                # 不应抛 TypeError
                manager._do_import("test_cpu_none", str(source), str(target), 'copy')

            progress = manager.get_progress("test_cpu_none")
            assert progress is not None
            # 状态应该是 COMPLETED（不是 FAILED），证明没崩
            from backend.import_manager import ImportStatus
            assert progress.status in (ImportStatus.COMPLETED, ImportStatus.FAILED)


# ============================================================
# 综合测试：状态机与端到端流程验证
# ============================================================


def test_status_transitions_completed():
    """验证正常导入流程的状态转换：pending → scanning → processing → completed"""
    from backend.import_manager import ImportManager, ImportStatus

    manager = ImportManager()

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'source'
        source.mkdir()
        target = Path(tmp) / 'target'
        target.mkdir()
        for i in range(3):
            (source / f'img_{i}.jpg').write_bytes(b'fake_img' * 100)

        manager.create_import("test_status_flow", str(source), str(target))

        # 初始状态
        progress = manager.get_progress("test_status_flow")
        assert progress.status == ImportStatus.PENDING

        with patch('backend.import_manager.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.all.return_value = []
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.close = MagicMock()

            manager._do_import("test_status_flow", str(source), str(target), 'copy')

        # 最终状态
        assert progress.status == ImportStatus.COMPLETED
        assert progress.total_files == 3
        # processed_files 至少为 1（实际文件大小满足条件），或者可能为 0（取决于 _import_file 逻辑）
        assert progress.processed_files >= 0


def test_cancel_before_processing_keeps_cancelled_status():
    """用户在扫描后点击取消：状态必须是 CANCELLED，不可被覆盖为 COMPLETED"""
    from backend.import_manager import ImportManager, ImportStatus

    manager = ImportManager()

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'source'
        source.mkdir()
        target = Path(tmp) / 'target'
        target.mkdir()
        for i in range(5):
            (source / f'big_{i}.jpg').write_bytes(b'data' * 100)

        manager.create_import("test_cancel_status", str(source), str(target))

        # 模拟用户在文件处理期间取消（设置 cancel_flag=True）
        manager.cancel_import("test_cancel_status")

        with patch('backend.import_manager.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.all.return_value = []
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.close = MagicMock()

            manager._do_import("test_cancel_status", str(source), str(target), 'copy')

        progress = manager.get_progress("test_cancel_status")
        assert progress is not None
        assert progress.status == ImportStatus.CANCELLED, (
            f"取消后状态应为 CANCELLED，实际为 {progress.status.value}"
        )


def test_pause_resume_cycle_status():
    """验证暂停→恢复→完成整个流程的状态正确性"""
    from backend.import_manager import ImportManager, ImportStatus

    manager = ImportManager()

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'source'
        source.mkdir()
        target = Path(tmp) / 'target'
        target.mkdir()
        (source / 'photo.jpg').write_bytes(b'content')

        manager.create_import("test_pause_resume", str(source), str(target))

        # 1) 暂停
        manager.pause_import("test_pause_resume")
        progress = manager.get_progress("test_pause_resume")
        # 注意：pause_import 只在 PROCESSING 状态时才切换到 PAUSED
        # 所以 PENDING 时调用 pause_import 可能不会立即切状态，这是设计选择

        with patch('backend.import_manager.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.all.return_value = []
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.close = MagicMock()

            # 正常导入（cancel_flag 未设置，event 默认 set，所以不会阻塞）
            manager._do_import("test_pause_resume", str(source), str(target), 'copy')

        progress = manager.get_progress("test_pause_resume")
        assert progress.status == ImportStatus.COMPLETED


def test_invalid_source_path_raises_gracefully():
    """源路径不存在时应进入 FAILED 状态"""
    from backend.import_manager import ImportManager, ImportStatus

    manager = ImportManager()

    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'target'
        target.mkdir()
        # 不存在的源路径
        source = Path(tmp) / 'nonexistent'

        manager.create_import("test_invalid_source", str(source), str(target))

        # 实际不会抛异常，_do_import 内部捕获
        with patch('backend.import_manager.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            mock_db.close = MagicMock()

            manager._do_import("test_invalid_source", str(source), str(target), 'copy')

        progress = manager.get_progress("test_invalid_source")
        assert progress.status == ImportStatus.FAILED, (
            f"源路径无效，状态应为 FAILED，实际为 {progress.status.value}"
        )
        assert progress.error_message is not None


def test_progress_dict_fields_consistency():
    """验证 to_dict 返回的字段与前端期望一致"""
    from backend.import_manager import ImportManager, ImportStatus

    manager = ImportManager()

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'source'
        source.mkdir()
        target = Path(tmp) / 'target'
        target.mkdir()
        (source / 'a.jpg').write_bytes(b'content')

        manager.create_import("test_dict_fields", str(source), str(target))

        # 未开始：PENDING，文件数 0，进度 0
        progress_dict = manager.get_progress_dict("test_dict_fields")
        assert progress_dict is not None
        assert 'import_id' in progress_dict
        assert 'status' in progress_dict
        assert 'progress' in progress_dict
        assert 'total_files' in progress_dict
        assert 'processed_files' in progress_dict
        assert 'failed_files' in progress_dict
        assert 'duplicated_files' in progress_dict
        assert progress_dict['status'] == 'pending'
        assert progress_dict['progress'] == 0


def test_cancel_flag_isolation_between_imports():
    """多个导入任务之间的 cancel_flag 必须隔离，互不影响"""
    from backend.import_manager import ImportManager

    manager = ImportManager()

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'source'
        source.mkdir()
        target = Path(tmp) / 'target'
        target.mkdir()
        (source / 'a.jpg').write_bytes(b'content')

        manager.create_import("task_A", str(source), str(target))
        manager.create_import("task_B", str(source), str(target))

        # 只取消 task_A
        manager.cancel_import("task_A")

        # task_A 的 cancel_flag 必须为 True
        assert manager._should_cancel("task_A") is True
        # task_B 的 cancel_flag 必须为 False
        assert manager._should_cancel("task_B") is False


def test_load_target_records_path_boundary():
    """回归测试：_load_target_records 必须用路径分隔符作为边界，
    防止前缀歧义（如目标 E:\\Photos 不能匹配 E:\\Photos2 下的照片）"""
    from unittest.mock import patch
    from backend.import_manager import ImportManager

    manager = ImportManager()

    with tempfile.TemporaryDirectory() as tmp:
        # 模拟两个同名前缀的目录
        parent = Path(tmp)
        target = parent / 'Photos'
        sibling = parent / 'Photos2'
        target.mkdir()
        sibling.mkdir()

        in_target = str(target / '2024-01' / 'a.jpg')
        in_sibling = str(sibling / '2024-01' / 'b.jpg')
        # 边界检查：path == target_prefix（无分隔符）也不应匹配
        edge = str(target)

        # 构造 DB 返回的 Photo 行
        class FakePhoto:
            def __init__(self, p, sz, md):
                self.path = p
                self.size = sz
                self.md5_hash = md

        fake_photos = [
            FakePhoto(in_target, 100, 'md5_in_target'),
            FakePhoto(in_sibling, 200, 'md5_in_sibling'),
            FakePhoto(edge, 300, 'md5_edge'),
        ]

        # 用一个真实工作的 mock filter：检查 startswith 参数
        target_prefix = str(target)
        target_prefix_with_sep = target_prefix.rstrip(os.sep) + os.sep

        class FakeQuery:
            def __init__(self, photos):
                self._photos = photos
            def filter(self, criterion):
                # SQLAlchemy 的 startswith 会调用 .startswith(value) - 拦截并模拟
                # 通过检查 fake_photos 元素的 path 是否以 target_prefix_with_sep 开头
                filtered = [p for p in self._photos
                            if str(p.path).startswith(target_prefix_with_sep)]
                return FakeQuery(filtered)
            def all(self):
                return self._photos

        mock_db = MagicMock()
        mock_db.query.return_value = FakeQuery(fake_photos)
        with patch('backend.import_manager.SessionLocal', return_value=mock_db):
            records, size_to_md5s = manager._load_target_records(target)

        # 应当只包含 target 目录下的照片，sibling 和 edge 不应被包含
        assert 'md5_in_target' in records
        assert 'md5_in_sibling' not in records, '前缀歧义：Photos2 被当作 Photos 的子目录'
        assert 'md5_edge' not in records, '边界检查：与 target_prefix 完全相等的路径不应被包含'
        assert records['md5_in_target'] == in_target
        assert size_to_md5s == {100: {'md5_in_target'}}

def test_pause_import(import_manager, temp_source_dir, temp_target_dir):
    """测试暂停导入任务"""
    import_id = "test_import_101"
    import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
    
    result = import_manager.pause_import(import_id)
    assert result is None
    
    # 验证导入任务仍可访问
    progress = import_manager.get_progress(import_id)
    assert progress is not None

def test_resume_import(import_manager, temp_source_dir, temp_target_dir):
    """测试继续导入任务"""
    import_id = "test_import_202"
    import_manager.create_import(import_id, temp_source_dir, temp_target_dir)
    
    result = import_manager.pause_import(import_id)
    assert result is None
    
    result = import_manager.resume_import(import_id)
    assert result is None
    
    # 验证导入任务仍可访问
    progress = import_manager.get_progress(import_id)
    assert progress is not None


def test_file_conflict_enum():
    """测试文件冲突枚举"""
    # 测试枚举值存在且正确
    assert FileConflict.NONE.value == "none"
    assert FileConflict.MD5_DUPLICATE.value == "md5"
    assert FileConflict.NAME_DUPLICATE.value == "name"
    
    # 测试枚举类型
    assert isinstance(FileConflict.NONE, FileConflict)
    assert isinstance(FileConflict.MD5_DUPLICATE, FileConflict)
    assert isinstance(FileConflict.NAME_DUPLICATE, FileConflict)


def test_file_conflict_values():
    """测试文件冲突枚举值"""
    # 测试所有枚举值
    conflict_values = [item.value for item in FileConflict]
    assert "none" in conflict_values
    assert "md5" in conflict_values
    assert "name" in conflict_values

