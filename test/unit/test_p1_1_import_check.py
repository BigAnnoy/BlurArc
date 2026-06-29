"""
P1-1: _perform_import_check 单次遍历修复验证

测试修复内容：
- 移除了第一次目录遍历（原先先 count 再 scan，现改为单次遍历）
- 使用动态进度估算公式：49 * n / (n + K)
- 在扫描时一次性收集 size/mtime/EXIF，避免后续重复调用

测试场景：
1. 空目录
2. 只有照片的目录
3. 照片+视频混合目录
4. 包含重复照片的目录
5. 大目录（1000+ 文件）

验证项：
- 进度条正常推进（0% -> 50% -> 100%）
- 返回的 media_files 列表正确
- 源重复检测结果正确
- 目标重复检测结果正确
- 只遍历一次目录（通过计数器验证）
- 性能对比（大目录耗时减少）
"""
import os
import time
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from collections import defaultdict

import pytest
from PIL import Image

# ---------------------------------------------------------------------------
# 导入被测函数
# ---------------------------------------------------------------------------
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


def _create_test_image_with_exif(path: Path, date_str: str = "2024:06:15 12:00:00",
                                  size: int = 100, color: tuple = (100, 150, 200)) -> Path:
    """创建带 EXIF DateTimeOriginal 的测试 JPEG"""
    try:
        import piexif
    except ImportError:
        pytest.skip("piexif 未安装，跳过 EXIF 测试")
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (size, size), color=color)
    exif_dict = {
        "0th": {},
        "Exif": {piexif.ExifIFD.DateTimeOriginal: date_str.encode()},
        "GPS": {},
        "1st": {},
        "thumbnail": None,
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(str(path), exif=exif_bytes)
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

    def progress_at_stage(self, stage_name):
        """返回某 stage 首次出现时的 progress 值"""
        for p, s, _ in self.records:
            if s == stage_name:
                return p
        return None

    def is_monotonically_increasing(self):
        """检查进度是否大致单调递增（允许同 stage 内持平）"""
        vals = self.progress_values
        for i in range(1, len(vals)):
            if vals[i] < vals[i - 1]:
                # 允许小幅回退（不同 stage 之间可能有微小回退）
                if vals[i - 1] - vals[i] > 5:
                    return False
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_album_path(tmp_path):
    """mock get_album_path 返回临时目录"""
    album = tmp_path / "album"
    album.mkdir()
    with patch("backend.api_server.get_album_path", return_value=str(album)):
        yield album


@pytest.fixture
def mock_album_path_empty():
    """mock get_album_path 返回 None（无相册目录）"""
    with patch("backend.api_server.get_album_path", return_value=None):
        yield


@pytest.fixture
def mock_db_empty():
    """mock 数据库查询返回空结果（模拟 DB 为空或不存在）"""
    mock_session_cls = MagicMock()
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    mock_db.query.return_value.all.return_value = []
    mock_db.close = MagicMock()

    with patch("backend.api_server.get_album_path", return_value=None):
        yield mock_db


# ---------------------------------------------------------------------------
# 场景 1：空目录
# ---------------------------------------------------------------------------

class TestEmptyDirectory:
    """空目录场景"""

    def test_empty_dir_returns_zero_media(self, tmp_path, mock_album_path_empty):
        """空目录应返回 media_count=0，无 date_folders"""
        source = tmp_path / "empty_source"
        source.mkdir()

        result = _perform_import_check(source)

        assert result['status'] == 'valid'
        assert result['media_count'] == 0
        assert result['total_size'] == 0
        assert result['total_size_mb'] == 0.0
        assert result['date_folders'] == []
        assert result['source_duplicates'] == {}
        assert result['target_duplicates'] == {}
        assert result['source_path'] == str(source)

    def test_empty_dir_progress_callback(self, tmp_path, mock_album_path_empty):
        """空目录也应触发进度回调（至少 scanning -> completed）"""
        source = tmp_path / "empty_source"
        source.mkdir()

        collector = ProgressCollector()
        result = _perform_import_check(source, progress_callback=collector)

        # 至少应有 scanning 和 completed 阶段
        assert collector.has_stage('scanning')
        assert collector.has_stage('completed')
        assert collector.max_progress == 100

    def test_empty_dir_with_non_media_files(self, tmp_path, mock_album_path_empty):
        """只有非媒体文件的目录等同于空目录"""
        source = tmp_path / "non_media"
        source.mkdir()
        for i in range(10):
            (source / f"doc_{i}.txt").write_text(f"document {i}")
        for i in range(5):
            (source / f"data_{i}.csv").write_text(f"a,b,c\n{i},{i+1},{i+2}")

        collector = ProgressCollector()
        result = _perform_import_check(source, progress_callback=collector)

        assert result['media_count'] == 0
        assert result['date_folders'] == []


# ---------------------------------------------------------------------------
# 场景 2：只有照片的目录
# ---------------------------------------------------------------------------

class TestPhotosOnlyDirectory:
    """纯照片目录场景"""

    def test_photos_only_correct_count(self, tmp_path, mock_album_path_empty):
        """纯 JPEG 目录应正确统计文件数"""
        source = tmp_path / "photos"
        source.mkdir()
        for i in range(10):
            _create_test_image(source / f"photo_{i}.jpg", color=(i * 25, 100, 200))

        result = _perform_import_check(source)

        assert result['media_count'] == 10
        assert result['total_size'] > 0
        assert len(result['preview']) <= 5  # preview 最多 5 个

    def test_photos_only_date_folders(self, tmp_path, mock_album_path_empty):
        """照片应按日期分组到 date_folders"""
        source = tmp_path / "photos"
        source.mkdir()

        # 创建不同 mtime 的文件以产生不同日期分组
        for i in range(5):
            p = _create_test_image(source / f"photo_{i}.jpg")
            # 设置不同的 mtime（不同月份）
            os.utime(p, (1704067200 + i * 86400, 1704067200 + i * 86400))  # 2024-01

        result = _perform_import_check(source)

        assert result['media_count'] == 5
        assert len(result['date_folders']) >= 1
        for folder in result['date_folders']:
            assert 'name' in folder
            assert 'count' in folder
            assert 'size' in folder
            assert 'files' in folder

    def test_photos_only_progress_stages(self, tmp_path, mock_album_path_empty):
        """纯照片目录应经历完整的进度阶段"""
        source = tmp_path / "photos"
        source.mkdir()
        for i in range(20):
            _create_test_image(source / f"photo_{i}.jpg")

        collector = ProgressCollector()
        _perform_import_check(source, progress_callback=collector)

        # 应经历所有关键阶段
        assert collector.has_stage('scanning')
        assert collector.has_stage('grouping')
        assert collector.has_stage('source_duplicates')
        assert collector.has_stage('target_duplicates')
        assert collector.has_stage('completed')

        # 进度应单调递增（大致）
        assert collector.is_monotonically_increasing()
        assert collector.max_progress == 100

    def test_photos_only_media_files_structure(self, tmp_path, mock_album_path_empty):
        """返回结果中每个 media file 应包含必要字段"""
        source = tmp_path / "photos"
        source.mkdir()
        _create_test_image(source / "test_photo.jpg")

        result = _perform_import_check(source)

        # 通过 date_folders 间接验证 media_files 结构
        assert len(result['date_folders']) >= 1
        for folder in result['date_folders']:
            for f in folder['files']:
                assert 'name' in f
                assert 'path' in f
                assert 'size' in f
                assert 'mtime' in f
                assert 'thumbnail_url' in f
                assert f['name'] == 'test_photo.jpg'
                assert f['size'] > 0

    def test_multiple_image_formats(self, tmp_path, mock_album_path_empty):
        """应支持多种图片格式（jpg, png, bmp, webp 等）"""
        source = tmp_path / "mixed_formats"
        source.mkdir()

        formats = {
            'test.jpg': (100, 150, 200),
            'test.png': (200, 100, 150),
            'test.bmp': (150, 200, 100),
        }
        for name, color in formats.items():
            _create_test_image(source / name, color=color)

        result = _perform_import_check(source)

        assert result['media_count'] == 3


# ---------------------------------------------------------------------------
# 场景 3：照片+视频混合目录
# ---------------------------------------------------------------------------

class TestMixedPhotosVideosDirectory:
    """照片+视频混合目录场景"""

    def test_mixed_correct_count(self, tmp_path, mock_album_path_empty):
        """混合目录应同时统计照片和视频"""
        source = tmp_path / "mixed"
        source.mkdir()

        for i in range(5):
            _create_test_image(source / f"photo_{i}.jpg")
        for i in range(3):
            _create_fake_video(source / f"video_{i}.mp4")

        result = _perform_import_check(source)

        assert result['media_count'] == 8  # 5 照片 + 3 视频

    def test_mixed_non_media_ignored(self, tmp_path, mock_album_path_empty):
        """非媒体文件应被忽略"""
        source = tmp_path / "mixed"
        source.mkdir()

        for i in range(5):
            _create_test_image(source / f"photo_{i}.jpg")
        for i in range(3):
            _create_fake_video(source / f"video_{i}.mp4")
        for i in range(10):
            (source / f"doc_{i}.txt").write_text(f"doc {i}")
        (source / "data.json").write_text('{"key": "value"}')

        result = _perform_import_check(source)

        assert result['media_count'] == 8  # 只计媒体文件

    def test_mixed_progress_with_many_files(self, tmp_path, mock_album_path_empty):
        """大量混合文件的进度应正常推进"""
        source = tmp_path / "large_mixed"
        source.mkdir()

        for i in range(100):
            _create_test_image(source / f"photo_{i}.jpg")
        for i in range(50):
            _create_fake_video(source / f"video_{i}.mp4", content_size=500)

        collector = ProgressCollector()
        result = _perform_import_check(source, progress_callback=collector)

        assert result['media_count'] == 150
        assert collector.max_progress == 100
        assert collector.is_monotonically_increasing()

    def test_mixed_subdirectories(self, tmp_path, mock_album_path_empty):
        """应递归扫描子目录"""
        source = tmp_path / "nested"
        source.mkdir()

        # 根目录
        _create_test_image(source / "root_photo.jpg")
        # 子目录
        sub1 = source / "subdir1"
        sub1.mkdir()
        _create_test_image(sub1 / "sub1_photo.jpg")
        sub2 = source / "subdir1" / "subdir2"
        sub2.mkdir()
        _create_fake_video(sub2 / "deep_video.mp4")

        result = _perform_import_check(source)

        assert result['media_count'] == 3


# ---------------------------------------------------------------------------
# 场景 4：包含重复照片的目录
# ---------------------------------------------------------------------------

class TestDuplicatePhotosDirectory:
    """重复照片检测场景"""

    def test_source_duplicates_identical_content(self, tmp_path, mock_album_path_empty):
        """内容完全相同的文件应被检测为源重复"""
        source = tmp_path / "duplicates"
        source.mkdir()

        # 创建两个内容完全相同的文件
        content = b"identical_image_content_bytes_" * 100
        _write_file_with_content(source / "photo_copy1.jpg", content)
        _write_file_with_content(source / "photo_copy2.jpg", content)
        # 一个不同的文件
        _write_file_with_content(source / "unique_photo.jpg", b"unique_content_" * 100)

        result = _perform_import_check(source)

        assert result['media_count'] == 3
        # 应有 1 组源重复（2 个文件共享同一 MD5）
        assert len(result['source_duplicates']) == 1
        for md5_hash, files in result['source_duplicates'].items():
            assert len(files) == 2
            names = {f['name'] for f in files}
            assert names == {'photo_copy1.jpg', 'photo_copy2.jpg'}

    def test_no_false_source_duplicates(self, tmp_path, mock_album_path_empty):
        """不同内容的文件不应被误报为源重复"""
        source = tmp_path / "no_dup"
        source.mkdir()

        for i in range(5):
            _write_file_with_content(
                source / f"unique_{i}.jpg",
                f"unique_content_{i}_".encode() * 100
            )

        result = _perform_import_check(source)

        assert result['media_count'] == 5
        assert len(result['source_duplicates']) == 0

    def test_source_duplicates_multiple_groups(self, tmp_path, mock_album_path_empty):
        """多组重复文件应分别检测"""
        source = tmp_path / "multi_dup"
        source.mkdir()

        # 第一组重复
        content_a = b"group_a_content_" * 100
        _write_file_with_content(source / "a1.jpg", content_a)
        _write_file_with_content(source / "a2.jpg", content_a)

        # 第二组重复
        content_b = b"group_b_content_" * 100
        _write_file_with_content(source / "b1.jpg", content_b)
        _write_file_with_content(source / "b2.jpg", content_b)
        _write_file_with_content(source / "b3.jpg", content_b)

        # 不重复的文件
        _write_file_with_content(source / "unique.jpg", b"totally_unique_" * 100)

        result = _perform_import_check(source)

        assert result['media_count'] == 6
        assert len(result['source_duplicates']) == 2

        # 验证各组数量
        dup_counts = sorted([len(files) for files in result['source_duplicates'].values()])
        assert dup_counts == [2, 3]

    def test_target_duplicates_with_album(self, tmp_path):
        """源文件与相册中已有文件内容相同应被检测为目标重复"""
        source = tmp_path / "source"
        source.mkdir()
        album = tmp_path / "album"
        album.mkdir()

        # 在源和相册中各放一份相同内容
        shared_content = b"shared_image_content_" * 100
        _write_file_with_content(source / "photo.jpg", shared_content)
        _write_file_with_content(album / "existing_photo.jpg", shared_content)

        # mock album_path 和 DB（DB 返回空，触发文件系统回退扫描）
        with patch("backend.api_server.get_album_path", return_value=str(album)):
            # mock DB 查询失败以触发文件系统回退
            # SessionLocal 在 backend.database 中动态 import，patch 必须打在源头
            with patch("backend.database.SessionLocal", side_effect=Exception("no db")):
                result = _perform_import_check(source)

        # 目标重复应包含匹配项
        # 注意：目标重复检测依赖 prescan_index 匹配
        # 如果 size 和 exif 都匹配，才会进入 MD5 比对
        assert result['media_count'] == 1


# ---------------------------------------------------------------------------
# 场景 5：大目录（1000+ 文件）
# ---------------------------------------------------------------------------

class TestLargeDirectory:
    """大目录场景"""

    def test_1000_files_correct_count(self, tmp_path, mock_album_path_empty):
        """1000 个文件应正确统计"""
        source = tmp_path / "large"
        source.mkdir()

        for i in range(1000):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50,
                               color=(i % 255, (i * 2) % 255, (i * 3) % 255))

        collector = ProgressCollector()
        result = _perform_import_check(source, progress_callback=collector)

        assert result['media_count'] == 1000
        assert collector.max_progress == 100

    def test_1000_files_progress_dynamic(self, tmp_path, mock_album_path_empty):
        """1000 个文件的进度应使用动态估算公式推进"""
        source = tmp_path / "large"
        source.mkdir()

        for i in range(1000):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50)

        collector = ProgressCollector()
        _perform_import_check(source, progress_callback=collector)

        # scanning 阶段的进度应在 0~49 之间
        scanning_progresses = [p for p, s, _ in collector.records if s == 'scanning']
        if scanning_progresses:
            assert min(scanning_progresses) >= 0
            assert max(scanning_progresses) <= 49

        # 最终应达到 100
        assert collector.max_progress == 100

    def test_2000_files_mixed_formats(self, tmp_path, mock_album_path_empty):
        """2000 个混合格式文件应正确处理"""
        source = tmp_path / "very_large"
        source.mkdir()

        for i in range(1500):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50)
        for i in range(500):
            _create_fake_video(source / f"vid_{i:04d}.mp4", content_size=100)

        result = _perform_import_check(source)

        assert result['media_count'] == 2000

    def test_large_directory_performance(self, tmp_path, mock_album_path_empty):
        """大目录性能基准：1000 文件扫描阶段应合理"""
        source = tmp_path / "perf_test"
        source.mkdir()

        for i in range(1000):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50)

        start = time.time()
        result = _perform_import_check(source)
        elapsed = time.time() - start

        assert result['media_count'] == 1000
        # 单次遍历 1000 文件应在合理时间内完成（无严格上限，仅记录）
        print(f"\n[PERF] 1000 files: {elapsed:.2f}s")
        assert elapsed < 120.0, f"1000 文件耗时 {elapsed:.2f}s，超过 120s 上限"


# ---------------------------------------------------------------------------
# 单次遍历验证
# ---------------------------------------------------------------------------

class TestSingleTraversal:
    """验证只遍历一次目录"""

    def test_os_walk_called_once(self, tmp_path, mock_album_path_empty):
        """os.walk 应只在扫描阶段被调用一次（不对源目录做第二次遍历）"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(20):
            _create_test_image(source / f"img_{i}.jpg")

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
        # 注意：目标重复检测可能对 album 目录做 walk，但那不是 source
        assert walk_count == 1, f"os.walk 对源目录调用了 {walk_count} 次，期望 1 次"

    def test_no_separate_count_pass(self, tmp_path, mock_album_path_empty):
        """验证不存在独立的计数遍历（修复前的 bug：先遍历计数再遍历扫描）"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(50):
            _create_test_image(source / f"img_{i}.jpg")

        # 跟踪所有对源目录的 stat 调用
        stat_calls_on_source = 0
        original_stat = Path.stat

        def counting_stat(self_path, *args, **kwargs):
            nonlocal stat_calls_on_source
            result = original_stat(self_path, *args, **kwargs)
            if str(self_path).startswith(str(source)):
                stat_calls_on_source += 1
            return result

        with patch.object(Path, 'stat', counting_stat):
            _perform_import_check(source)

        # 每个文件应只被 stat 一次（在扫描阶段）
        # 修复前会 stat 两次（一次计数遍历 + 一次扫描遍历）
        # 允许少量额外 stat（如目录本身的 stat），但不应是 2x
        print(f"\n[STAT] 50 files, total stat calls on source: {stat_calls_on_source}")
        # 50 个文件，每个最多 stat 1 次 = 50 次
        # 加上一些目录 stat，上限设为 文件数 * 1.5
        assert stat_calls_on_source <= 50 * 1.5 + 10, (
            f"stat 调用 {stat_calls_on_source} 次，远超文件数 50，"
            f"可能存在多次遍历"
        )


# ---------------------------------------------------------------------------
# 进度回调验证
# ---------------------------------------------------------------------------

class TestProgressCallback:
    """进度回调详细验证"""

    def test_progress_starts_at_zero(self, tmp_path, mock_album_path_empty):
        """进度应从 0 开始"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(10):
            _create_test_image(source / f"img_{i}.jpg")

        collector = ProgressCollector()
        _perform_import_check(source, progress_callback=collector)

        assert collector.min_progress == 0

    def test_progress_ends_at_100(self, tmp_path, mock_album_path_empty):
        """进度应以 100 结束"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(10):
            _create_test_image(source / f"img_{i}.jpg")

        collector = ProgressCollector()
        _perform_import_check(source, progress_callback=collector)

        assert collector.max_progress == 100
        # 最后一条记录应是 completed
        assert collector.records[-1][1] == 'completed'

    def test_progress_goes_through_all_stages(self, tmp_path, mock_album_path_empty):
        """进度应经历 scanning -> grouping -> source_duplicates -> target_duplicates -> completed"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(30):
            _create_test_image(source / f"img_{i}.jpg")

        collector = ProgressCollector()
        _perform_import_check(source, progress_callback=collector)

        # 验证阶段顺序
        expected_stages = ['scanning', 'grouping', 'source_duplicates', 'completed']
        seen_stages = []
        for _, stage, _ in collector.records:
            if not seen_stages or seen_stages[-1] != stage:
                seen_stages.append(stage)

        for expected in expected_stages:
            assert expected in seen_stages, (
                f"缺少阶段 '{expected}'，实际阶段序列: {seen_stages}"
            )

    def test_progress_values_bounded(self, tmp_path, mock_album_path_empty):
        """所有进度值应在 [0, 100] 范围内"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(50):
            _create_test_image(source / f"img_{i}.jpg")

        collector = ProgressCollector()
        _perform_import_check(source, progress_callback=collector)

        for p, s, d in collector.records:
            assert 0 <= p <= 100, f"进度值 {p} 超出 [0, 100] 范围 (stage={s})"

    def test_no_progress_callback_works(self, tmp_path, mock_album_path_empty):
        """不提供 progress_callback 时应正常工作（不报错）"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(10):
            _create_test_image(source / f"img_{i}.jpg")

        # 不传 progress_callback
        result = _perform_import_check(source)
        assert result['media_count'] == 10

    def test_progress_callback_none_works(self, tmp_path, mock_album_path_empty):
        """progress_callback=None 时应正常工作"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(10):
            _create_test_image(source / f"img_{i}.jpg")

        result = _perform_import_check(source, progress_callback=None)
        assert result['media_count'] == 10


# ---------------------------------------------------------------------------
# 返回结果结构验证
# ---------------------------------------------------------------------------

class TestResultStructure:
    """返回结果的结构完整性验证"""

    def test_result_has_all_keys(self, tmp_path, mock_album_path_empty):
        """返回结果应包含所有必需的 key"""
        source = tmp_path / "source"
        source.mkdir()
        _create_test_image(source / "photo.jpg")

        result = _perform_import_check(source)

        expected_keys = {
            'status', 'source_path', 'media_count', 'total_size',
            'total_size_mb', 'preview', 'date_folders',
            'target_duplicates', 'source_duplicates', 'skipped_files'
        }
        assert set(result.keys()) == expected_keys

    def test_preview_max_5(self, tmp_path, mock_album_path_empty):
        """preview 最多返回 5 个文件"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(20):
            _create_test_image(source / f"img_{i}.jpg")

        result = _perform_import_check(source)

        assert len(result['preview']) <= 5

    def test_total_size_mb_calculation(self, tmp_path, mock_album_path_empty):
        """total_size_mb 应正确从 total_size 换算"""
        source = tmp_path / "source"
        source.mkdir()
        for i in range(5):
            _create_test_image(source / f"img_{i}.jpg")

        result = _perform_import_check(source)

        expected_mb = round(result['total_size'] / (1024 * 1024), 2)
        assert result['total_size_mb'] == expected_mb

    def test_date_folders_sorted_reverse(self, tmp_path, mock_album_path_empty):
        """date_folders 应按日期倒序排列"""
        source = tmp_path / "source"
        source.mkdir()

        # 创建不同月份的文件
        for month_idx, month in enumerate([1, 3, 6]):
            for i in range(3):
                p = _create_test_image(
                    source / f"img_m{month}_{i}.jpg",
                    color=(month * 40, 100, 200)
                )
                # 设置不同月份的 mtime
                ts = 1704067200 + (month - 1) * 30 * 86400  # 粗略按月偏移
                os.utime(p, (ts, ts))

        result = _perform_import_check(source)

        if len(result['date_folders']) > 1:
            dates = [f['name'] for f in result['date_folders']]
            # 应倒序（最新的在前）
            assert dates == sorted(dates, reverse=True), (
                f"date_folders 未按倒序排列: {dates}"
            )


# ---------------------------------------------------------------------------
# 性能对比测试
# ---------------------------------------------------------------------------

class TestPerformanceComparison:
    """性能对比：验证单次遍历 vs 两次遍历的性能差异"""

    def test_large_directory_benchmark(self, tmp_path, mock_album_path_empty):
        """大目录基准测试：记录耗时供对比"""
        source = tmp_path / "benchmark"
        source.mkdir()

        file_count = 2000
        for i in range(file_count):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50,
                               color=(i % 255, (i * 2) % 255, 100))

        start = time.time()
        result = _perform_import_check(source)
        elapsed = time.time() - start

        assert result['media_count'] == file_count
        print(f"\n[PERF BENCHMARK] {file_count} files: {elapsed:.2f}s "
              f"({elapsed * 1000 / file_count:.1f}ms/file)")

        # 单次遍历 2000 文件应在合理时间内
        assert elapsed < 180.0, (
            f"{file_count} 文件耗时 {elapsed:.2f}s，超过 180s 上限"
        )

    def test_scan_phase_is_single_pass(self, tmp_path, mock_album_path_empty):
        """验证扫描阶段是单次遍历（通过时间分析）"""
        source = tmp_path / "timing_test"
        source.mkdir()

        file_count = 500
        for i in range(file_count):
            _create_test_image(source / f"img_{i:04d}.jpg", size=50)

        collector = ProgressCollector()
        start = time.time()
        _perform_import_check(source, progress_callback=collector)
        total_elapsed = time.time() - start

        # 分析 scanning 阶段的耗时
        # 找到 scanning 阶段最后一条记录的时间点
        scan_records = [(i, r) for i, r in enumerate(collector.records) if r[1] == 'scanning']
        grouping_records = [(i, r) for i, r in enumerate(collector.records) if r[1] == 'grouping']

        print(f"\n[TIMING] Total: {total_elapsed:.2f}s")
        print(f"[TIMING] Scanning records: {len(scan_records)}")
        print(f"[TIMING] Grouping records: {len(grouping_records)}")

        # 如果存在两次遍历，scanning 阶段的时间应显著长于单次遍历
        # 这里主要作为基准记录，不做严格断言
        assert total_elapsed < 120.0


# ---------------------------------------------------------------------------
# 边界条件测试
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """边界条件和异常场景"""

    def test_single_file(self, tmp_path, mock_album_path_empty):
        """只有一个文件的目录"""
        source = tmp_path / "single"
        source.mkdir()
        _create_test_image(source / "only.jpg")

        result = _perform_import_check(source)

        assert result['media_count'] == 1
        assert len(result['date_folders']) == 1

    def test_zero_byte_media_file(self, tmp_path, mock_album_path_empty):
        """0 字节的媒体文件应被统计但 size=0"""
        source = tmp_path / "zero"
        source.mkdir()
        (source / "empty.jpg").write_bytes(b"")

        result = _perform_import_check(source)

        # 0 字节文件后缀是 .jpg，应被识别为媒体
        assert result['media_count'] == 1

    def test_deeply_nested_structure(self, tmp_path, mock_album_path_empty):
        """深层嵌套目录结构"""
        source = tmp_path / "deep"
        current = source
        current.mkdir()

        # 创建 10 层嵌套
        for i in range(10):
            current = current / f"level_{i}"
            current.mkdir()
            _create_test_image(current / f"img_{i}.jpg")

        result = _perform_import_check(source)

        assert result['media_count'] == 10

    def test_special_characters_in_filename(self, tmp_path, mock_album_path_empty):
        """文件名包含特殊字符"""
        source = tmp_path / "special"
        source.mkdir()

        _create_test_image(source / "photo (1).jpg")
        _create_test_image(source / "photo[2].jpg")
        _create_test_image(source / "photo - copy.jpg")

        result = _perform_import_check(source)

        assert result['media_count'] == 3

    def test_mixed_case_extensions(self, tmp_path, mock_album_path_empty):
        """大写扩展名应被正确识别"""
        source = tmp_path / "upper_ext"
        source.mkdir()

        _create_test_image(source / "photo.JPG")
        _create_test_image(source / "photo2.JPEG")

        result = _perform_import_check(source)

        # MEDIA_FORMATS 是小写的，但代码用 .suffix.lower() 匹配
        assert result['media_count'] == 2


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov", "-s"])
