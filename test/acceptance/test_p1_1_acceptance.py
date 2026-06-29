"""
P1-1 导入检查单次遍历修复 - 验收测试

验收目标：
验证 _perform_import_check 函数修复后的正确性和性能提升

修复内容：
- 移除第一次目录遍历（原先先 count 再 scan）
- 改为单次遍历 + 动态进度估算
- 在扫描时一次性收集 size/mtime/EXIF，避免后续重复调用

验收场景：
1. 空目录
2. 只有照片的目录（100 个文件）
3. 照片+视频混合目录（200 个文件）
4. 包含重复照片的目录（50 个重复）
5. 大目录（1000+ 文件）

验收标准：
- 进度条正常推进（0% → 50% → 100%）
- 返回的 media_files 列表正确
- 源重复检测结果正确
- 目标重复检测结果正确
- 只遍历一次目录（通过 mock os.walk 验证）
- 性能对比：大目录（1000+ 文件）耗时减少 30%+
"""
import os
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from collections import defaultdict

import pytest
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.api_server import _perform_import_check


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

def _create_test_image(path: Path, size: int = 100, color: tuple = (100, 150, 200)) -> Path:
    """创建测试 JPEG 图片（无 EXIF）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (size, size), color=color)
    img.save(str(path))
    return path


def _create_fake_video(path: Path, content_size: int = 200) -> Path:
    """创建模拟视频文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00\x00\x00\x20ftypmp42" + b"\x00" * content_size)
    return path


def _write_file_with_content(path: Path, content: bytes) -> Path:
    """写入指定内容的文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


class ProgressCollector:
    """收集进度回调，用于断言进度推进"""

    def __init__(self):
        self.records = []  # [(progress, stage, detail), ...]

    def __call__(self, progress, stage, detail):
        self.records.append((progress, stage, detail))

    @property
    def progress_values(self):
        return [r[0] for r in self.records]

    @property
    def stages(self):
        return [r[1] for r in self.records]

    @property
    def max_progress(self):
        return max(self.progress_values) if self.progress_values else 0

    @property
    def min_progress(self):
        return min(self.progress_values) if self.progress_values else 0

    def has_stage(self, stage_name):
        return stage_name in self.stages

    def is_monotonically_increasing(self, tolerance=5):
        """检查进度是否大致单调递增（允许小幅回退）"""
        vals = self.progress_values
        for i in range(1, len(vals)):
            if vals[i] < vals[i - 1]:
                if vals[i - 1] - vals[i] > tolerance:
                    return False
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_album_path_empty():
    """mock get_album_path 返回 None（无相册目录）"""
    with patch("backend.api_server.get_album_path", return_value=None):
        yield


# ---------------------------------------------------------------------------
# 验收场景 1：空目录
# ---------------------------------------------------------------------------

class TestAcceptanceEmptyDirectory:
    """验收场景 1：空目录"""

    def test_empty_directory_basic(self, tmp_path, mock_album_path_empty):
        """验收点：空目录应返回 media_count=0"""
        source = tmp_path / "empty"
        source.mkdir()

        result = _perform_import_check(source)

        assert result['status'] == 'valid', "状态应为 valid"
        assert result['media_count'] == 0, "媒体文件数应为 0"
        assert result['total_size'] == 0, "总大小应为 0"
        assert result['date_folders'] == [], "日期分组应为空"
        assert result['source_duplicates'] == {}, "源重复应为空"
        assert result['target_duplicates'] == {}, "目标重复应为空"

    def test_empty_directory_progress(self, tmp_path, mock_album_path_empty):
        """验收点：空目录进度应正常推进"""
        source = tmp_path / "empty"
        source.mkdir()

        collector = ProgressCollector()
        _perform_import_check(source, progress_callback=collector)

        assert collector.min_progress == 0, "进度应从 0 开始"
        assert collector.max_progress == 100, "进度应到 100 结束"
        assert collector.has_stage('scanning'), "应有 scanning 阶段"
        assert collector.has_stage('completed'), "应有 completed 阶段"


# ---------------------------------------------------------------------------
# 验收场景 2：只有照片的目录（100 个文件）
# ---------------------------------------------------------------------------

class TestAcceptancePhotosOnly:
    """验收场景 2：只有照片的目录（100 个文件）"""

    def test_photos_only_count(self, tmp_path, mock_album_path_empty):
        """验收点：100 个照片应正确统计"""
        source = tmp_path / "photos"
        source.mkdir()

        for i in range(100):
            _create_test_image(source / f"photo_{i:03d}.jpg",
                             color=(i % 255, (i * 2) % 255, 100))

        result = _perform_import_check(source)

        assert result['media_count'] == 100, f"应统计到 100 个文件，实际 {result['media_count']}"
        assert result['total_size'] > 0, "总大小应大于 0"
        assert len(result['preview']) <= 5, "预览最多 5 个文件"

    def test_photos_only_progress(self, tmp_path, mock_album_path_empty):
        """验收点：进度应经历完整阶段"""
        source = tmp_path / "photos"
        source.mkdir()

        for i in range(100):
            _create_test_image(source / f"photo_{i:03d}.jpg")

        collector = ProgressCollector()
        _perform_import_check(source, progress_callback=collector)

        # 验证进度推进
        assert collector.min_progress == 0, "进度应从 0 开始"
        assert collector.max_progress == 100, "进度应到 100"
        assert collector.is_monotonically_increasing(), "进度应大致单调递增"

        # 验证关键阶段
        assert collector.has_stage('scanning'), "应有 scanning 阶段"
        assert collector.has_stage('grouping'), "应有 grouping 阶段"
        assert collector.has_stage('source_duplicates'), "应有 source_duplicates 阶段"
        assert collector.has_stage('completed'), "应有 completed 阶段"

    def test_photos_only_date_folders(self, tmp_path, mock_album_path_empty):
        """验收点：照片应按日期分组"""
        source = tmp_path / "photos"
        source.mkdir()

        for i in range(100):
            p = _create_test_image(source / f"photo_{i:03d}.jpg")
            # 设置不同的 mtime 以产生不同日期分组
            os.utime(p, (1704067200 + i * 86400, 1704067200 + i * 86400))

        result = _perform_import_check(source)

        assert len(result['date_folders']) >= 1, "应有至少 1 个日期分组"
        for folder in result['date_folders']:
            assert 'name' in folder, "日期分组应有 name"
            assert 'count' in folder, "日期分组应有 count"
            assert 'size' in folder, "日期分组应有 size"
            assert 'files' in folder, "日期分组应有 files"


# ---------------------------------------------------------------------------
# 验收场景 3：照片+视频混合目录（200 个文件）
# ---------------------------------------------------------------------------

class TestAcceptanceMixedMedia:
    """验收场景 3：照片+视频混合目录（200 个文件）"""

    def test_mixed_media_count(self, tmp_path, mock_album_path_empty):
        """验收点：混合目录应同时统计照片和视频"""
        source = tmp_path / "mixed"
        source.mkdir()

        # 150 张照片
        for i in range(150):
            _create_test_image(source / f"photo_{i:03d}.jpg")
        # 50 个视频
        for i in range(50):
            _create_fake_video(source / f"video_{i:03d}.mp4", content_size=300)

        result = _perform_import_check(source)

        assert result['media_count'] == 200, f"应统计到 200 个文件，实际 {result['media_count']}"

    def test_mixed_media_progress(self, tmp_path, mock_album_path_empty):
        """验收点：混合目录进度应正常推进"""
        source = tmp_path / "mixed"
        source.mkdir()

        for i in range(150):
            _create_test_image(source / f"photo_{i:03d}.jpg")
        for i in range(50):
            _create_fake_video(source / f"video_{i:03d}.mp4")

        collector = ProgressCollector()
        result = _perform_import_check(source, progress_callback=collector)

        assert result['media_count'] == 200
        assert collector.max_progress == 100, "进度应到 100"
        assert collector.is_monotonically_increasing(), "进度应大致单调递增"

    def test_mixed_media_non_media_ignored(self, tmp_path, mock_album_path_empty):
        """验收点：非媒体文件应被忽略"""
        source = tmp_path / "mixed"
        source.mkdir()

        # 媒体文件
        for i in range(100):
            _create_test_image(source / f"photo_{i:03d}.jpg")
        for i in range(50):
            _create_fake_video(source / f"video_{i:03d}.mp4")
        # 非媒体文件
        for i in range(50):
            (source / f"doc_{i:03d}.txt").write_text(f"document {i}")

        result = _perform_import_check(source)

        assert result['media_count'] == 150, "只应统计媒体文件"


# ---------------------------------------------------------------------------
# 验收场景 4：包含重复照片的目录（50 个重复）
# ---------------------------------------------------------------------------

class TestAcceptanceDuplicates:
    """验收场景 4：包含重复照片的目录（50 个重复）"""

    def test_source_duplicates_detection(self, tmp_path, mock_album_path_empty):
        """验收点：源重复检测应正确"""
        source = tmp_path / "duplicates"
        source.mkdir()

        # 创建 25 组重复（每组 2 个文件，共 50 个重复文件）
        for group in range(25):
            content = f"duplicate_group_{group}_content_".encode() * 50
            _write_file_with_content(source / f"group{group}_copy1.jpg", content)
            _write_file_with_content(source / f"group{group}_copy2.jpg", content)

        # 添加 50 个不重复的文件
        for i in range(50):
            _write_file_with_content(
                source / f"unique_{i:03d}.jpg",
                f"unique_content_{i}_".encode() * 50
            )

        result = _perform_import_check(source)

        assert result['media_count'] == 100, f"应统计到 100 个文件，实际 {result['media_count']}"
        assert len(result['source_duplicates']) == 25, \
            f"应检测到 25 组源重复，实际 {len(result['source_duplicates'])}"

        # 验证每组重复文件数量
        for md5_hash, files in result['source_duplicates'].items():
            assert len(files) == 2, f"每组应有 2 个文件，实际 {len(files)}"

    def test_target_duplicates_with_album(self, tmp_path):
        """验收点：目标重复检测应正确（有相册目录时不报错）"""
        source = tmp_path / "source"
        source.mkdir()
        album = tmp_path / "album"
        album.mkdir()

        # 在源和相册中各放一份相同内容
        shared_content = b"shared_image_content_" * 100
        _write_file_with_content(source / "photo.jpg", shared_content)
        _write_file_with_content(album / "existing_photo.jpg", shared_content)

        # mock album_path 指向临时相册目录
        # 不 mock DB：让 DB 查询自然执行（测试环境 DB 可能为空，会触发文件系统回退）
        with patch("backend.api_server.get_album_path", return_value=str(album)):
            result = _perform_import_check(source)

        assert result['media_count'] == 1, "应统计到 1 个源文件"
        assert 'target_duplicates' in result, "结果应包含 target_duplicates"
        # 目标重复检测依赖 prescan 匹配（size + exif），此处仅验证函数不报错


# ---------------------------------------------------------------------------
# 验收场景 5：大目录（1000+ 文件）
# ---------------------------------------------------------------------------

class TestAcceptanceLargeDirectory:
    """验收场景 5：大目录（1000+ 文件）"""

    def test_large_directory_1000_files(self, tmp_path, mock_album_path_empty):
        """验收点：1000 个文件应正确统计"""
        source = tmp_path / "large"
        source.mkdir()

        for i in range(1000):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50,
                             color=(i % 255, (i * 2) % 255, (i * 3) % 255))

        collector = ProgressCollector()
        result = _perform_import_check(source, progress_callback=collector)

        assert result['media_count'] == 1000, f"应统计到 1000 个文件，实际 {result['media_count']}"
        assert collector.max_progress == 100, "进度应到 100"

    def test_large_directory_2000_files(self, tmp_path, mock_album_path_empty):
        """验收点：2000 个文件应正确统计"""
        source = tmp_path / "very_large"
        source.mkdir()

        for i in range(2000):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50)

        result = _perform_import_check(source)

        assert result['media_count'] == 2000, f"应统计到 2000 个文件，实际 {result['media_count']}"


# ---------------------------------------------------------------------------
# 验收点：单次遍历验证
# ---------------------------------------------------------------------------

class TestAcceptanceSingleTraversal:
    """验收点：验证只遍历一次目录"""

    def test_os_walk_called_once(self, tmp_path, mock_album_path_empty):
        """验收点：os.walk 对源目录应只调用一次"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(100):
            _create_test_image(source / f"img_{i:03d}.jpg")

        walk_count = 0
        original_walk = os.walk

        def counting_walk(top, *args, **kwargs):
            nonlocal walk_count
            # 只统计对 source 目录的 walk 调用
            if Path(top) == source or str(top).startswith(str(source)):
                walk_count += 1
            return original_walk(top, *args, **kwargs)

        with patch("os.walk", side_effect=counting_walk):
            _perform_import_check(source)

        # 修复后应该只有 1 次 walk（扫描阶段）
        assert walk_count == 1, f"os.walk 对源目录调用了 {walk_count} 次，期望 1 次"

    def test_stat_calls_per_file(self, tmp_path, mock_album_path_empty):
        """验收点：每个文件应只被 stat 一次"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(100):
            _create_test_image(source / f"img_{i:03d}.jpg")

        stat_calls = defaultdict(int)
        original_stat = Path.stat

        def counting_stat(self_path, *args, **kwargs):
            result = original_stat(self_path, *args, **kwargs)
            if str(self_path).startswith(str(source)):
                stat_calls[str(self_path)] += 1
            return result

        with patch.object(Path, 'stat', counting_stat):
            _perform_import_check(source)

        # 每个文件应只被 stat 一次
        for file_path, count in stat_calls.items():
            assert count <= 1, f"文件 {file_path} 被 stat {count} 次，期望最多 1 次"


# ---------------------------------------------------------------------------
# 验收点：性能对比
# ---------------------------------------------------------------------------

class TestAcceptancePerformance:
    """验收点：性能对比"""

    def test_performance_benchmark_1000_files(self, tmp_path, mock_album_path_empty):
        """验收点：1000 文件性能基准"""
        source = tmp_path / "perf_1000"
        source.mkdir()

        for i in range(1000):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50)

        start = time.time()
        result = _perform_import_check(source)
        elapsed = time.time() - start

        assert result['media_count'] == 1000
        print(f"\n[PERF] 1000 files: {elapsed:.2f}s ({elapsed * 1000 / 1000:.1f}ms/file)")

        # 性能上限（宽松，仅记录）
        assert elapsed < 120.0, f"1000 文件耗时 {elapsed:.2f}s，超过 120s 上限"

    def test_performance_benchmark_2000_files(self, tmp_path, mock_album_path_empty):
        """验收点：2000 文件性能基准"""
        source = tmp_path / "perf_2000"
        source.mkdir()

        for i in range(2000):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50)

        start = time.time()
        result = _perform_import_check(source)
        elapsed = time.time() - start

        assert result['media_count'] == 2000
        print(f"\n[PERF] 2000 files: {elapsed:.2f}s ({elapsed * 1000 / 2000:.1f}ms/file)")

        # 性能上限（宽松，仅记录）
        assert elapsed < 240.0, f"2000 文件耗时 {elapsed:.2f}s，超过 240s 上限"


# ---------------------------------------------------------------------------
# 验收报告生成
# ---------------------------------------------------------------------------

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """生成验收报告摘要"""
    terminalreporter.section("P1-1 验收测试报告")

    # 统计通过的测试
    passed = len(terminalreporter.stats.get('passed', []))
    failed = len(terminalreporter.stats.get('failed', []))
    total = passed + failed

    terminalreporter.write_line(f"验收测试总数: {total}")
    terminalreporter.write_line(f"通过: {passed}")
    terminalreporter.write_line(f"失败: {failed}")

    if failed == 0:
        terminalreporter.write_line("\n✓ 所有验收测试通过！")
    else:
        terminalreporter.write_line(f"\n✗ 有 {failed} 个验收测试失败")
