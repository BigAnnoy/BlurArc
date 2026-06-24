"""
build_dest_filename 原子计数器专项测试
========================================

v0.6 优化 6 — 验证：
1. 基础功能：序号递增、_dup 后缀、taken_names 冲突检测
2. 并发安全：100 线程同时生成，结果全部唯一（无 race condition）
3. 计数器持久性：跨多次调用累计递增（不重置）
"""
import threading
import pytest
from pathlib import Path
from datetime import datetime

from backend.dest_filename import (
    build_dest_filename,
    reset_counter,
    _next_seq,
    _filename_lock,
)


@pytest.fixture(autouse=True)
def reset_state():
    """每个测试前重置计数器，避免跨测试污染"""
    reset_counter()
    yield
    # 测试结束后再重置一次（确保不影响其他测试）
    reset_counter()


class TestBuildDestFilename:
    """基础功能"""

    def test_first_call_returns_001(self, tmp_path):
        """首次调用应返回 _001 后缀"""
        path = build_dest_filename(
            datetime(2024, 1, 1, 12, 0, 0),
            ".jpg", tmp_path, False, set()
        )
        assert path.name == "20240101_120000_001.jpg"

    def test_increments_sequence(self, tmp_path):
        """连续 5 次调用应递增 001-005"""
        taken = set()
        paths = [
            build_dest_filename(datetime(2024, 1, 1, 12, 0, 0), ".jpg", tmp_path, False, taken)
            for _ in range(5)
        ]
        names = [p.name for p in paths]
        assert names == [
            "20240101_120000_001.jpg",
            "20240101_120000_002.jpg",
            "20240101_120000_003.jpg",
            "20240101_120000_004.jpg",
            "20240101_120000_005.jpg",
        ]

    def test_dup_suffix(self, tmp_path):
        """is_dup=True 应加 _dup 后缀"""
        path = build_dest_filename(
            datetime(2024, 1, 1, 12, 0, 0), ".jpg", tmp_path, True, set()
        )
        assert "_dup" in path.name
        assert path.name == "20240101_120000_001_dup.jpg"

    def test_taken_names_prevents_collision(self, tmp_path):
        """taken_names 已占用 → 跳过该序号"""
        taken = {"20240101_120000_001.jpg"}
        path = build_dest_filename(
            datetime(2024, 1, 1, 12, 0, 0), ".jpg", tmp_path, False, taken
        )
        # 应跳过 001，生成 002
        assert "001.jpg" not in path.name
        assert path.name == "20240101_120000_002.jpg"

    def test_taken_names_with_dup(self, tmp_path):
        """taken_names 包含 _dup 也应被跳过（只对 is_dup 形态生效）"""
        # 占用 001 的普通形态 + 001 的 dup 形态
        # 当 is_dup=True 时，001_dup 已被占用 → 跳到 002_dup
        taken = {"20240101_120000_001.jpg", "20240101_120000_001_dup.jpg"}
        path = build_dest_filename(
            datetime(2024, 1, 1, 12, 0, 0), ".jpg", tmp_path, True, taken
        )
        # 跳过 001_dup（已占用），应到 002_dup
        assert path.name == "20240101_120000_002_dup.jpg"

    def test_different_dates_get_different_stem(self, tmp_path):
        """不同日期应使用不同的 stem"""
        p1 = build_dest_filename(datetime(2024, 1, 1, 12, 0, 0), ".jpg", tmp_path, False, set())
        p2 = build_dest_filename(datetime(2024, 2, 1, 12, 0, 0), ".jpg", tmp_path, False, set())
        assert p1.name.startswith("20240101_")
        assert p2.name.startswith("20240201_")
        # 但计数器是全局递增，所以序号也递增
        assert p1.name == "20240101_120000_001.jpg"
        assert p2.name == "20240201_120000_002.jpg"

    def test_different_extensions(self, tmp_path):
        """不同扩展名应保留"""
        p_jpg = build_dest_filename(datetime(2024, 1, 1), ".jpg", tmp_path, False, set())
        p_mp4 = build_dest_filename(datetime(2024, 1, 1), ".mp4", tmp_path, False, set())
        assert p_jpg.suffix == ".jpg"
        assert p_mp4.suffix == ".mp4"

    def test_returns_path_with_correct_directory(self, tmp_path):
        """返回的路径应在指定目录下"""
        month_dir = tmp_path / "2024-01"
        path = build_dest_filename(
            datetime(2024, 1, 1), ".jpg", month_dir, False, set()
        )
        assert path.parent == month_dir


class TestConcurrentSafety:
    """并发安全"""

    def test_concurrent_generates_unique_filenames(self, tmp_path):
        """100 个线程同时生成，应全部唯一"""
        taken = set()
        taken_lock = threading.Lock()
        results = []
        errors = []

        def generate(i):
            try:
                path = build_dest_filename(
                    datetime(2024, 1, 1, 12, 0, 0),
                    ".jpg", tmp_path, False, taken
                )
                with taken_lock:
                    results.append(path.name)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=generate, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证
        assert not errors, f"线程异常: {errors[:3]}"
        assert len(results) == 100, f"应生成 100 个，实际 {len(results)}"
        assert len(set(results)) == 100, (
            f"检测到命名冲突: {len(results) - len(set(results))} 个"
        )

    def test_concurrent_mixed_dup_and_normal(self, tmp_path):
        """混合 dup + normal 场景的并发安全"""
        taken = set()
        taken_lock = threading.Lock()
        results = []

        def generate(is_dup):
            path = build_dest_filename(
                datetime(2024, 1, 1, 12, 0, 0),
                ".jpg", tmp_path, is_dup, taken
            )
            with taken_lock:
                results.append(path.name)

        threads = []
        for i in range(50):
            threads.append(threading.Thread(target=generate, args=(False,)))
            threads.append(threading.Thread(target=generate, args=(True,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 100
        assert len(set(results)) == 100, "混合 dup+normal 时检测到冲突"
        # 验证 50 个有 _dup，50 个没有
        dup_count = sum(1 for n in results if "_dup" in n)
        normal_count = sum(1 for n in results if "_dup" not in n)
        assert dup_count == 50
        assert normal_count == 50

    def test_concurrent_with_preloaded_taken(self, tmp_path):
        """预填充 taken_names 时并发仍安全"""
        # 预填 5 个占用名
        taken = {f"20240101_120000_{i:03d}.jpg" for i in range(1, 6)}
        taken_lock = threading.Lock()
        results = []
        errors = []

        def generate(i):
            try:
                path = build_dest_filename(
                    datetime(2024, 1, 1, 12, 0, 0),
                    ".jpg", tmp_path, False, taken
                )
                with taken_lock:
                    results.append(path.name)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=generate, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 50
        assert len(set(results)) == 50
        # 全部不应包含 001-005
        for name in results:
            seq = name.split("_")[-1].split(".")[0]
            assert int(seq) >= 6, f"生成了被占用的序号: {name}"


class TestCounterPersistence:
    """计数器持久性（与 taken_names 无关）"""

    def test_counter_persists_across_calls(self, tmp_path):
        """计数器应保持递增（跨调用不重置）"""
        for _ in range(10):
            build_dest_filename(
                datetime(2024, 1, 1, 12, 0, 0), ".jpg", tmp_path, False, set()
            )
        # 内部计数器已递增到 10，下一次 _next_seq() 应返回 11
        assert _next_seq() == 11

    def test_counter_independent_of_taken(self, tmp_path):
        """taken_names 中的占用不会让计数器回退"""
        # 预填 1000 个占用名（stem 与 media_date 一致）
        stem_dt = datetime(2024, 1, 1, 12, 0, 0)
        stem = stem_dt.strftime("%Y%m%d_%H%M%S")
        taken = {f"{stem}_{i:03d}.jpg" for i in range(1, 1001)}
        # 1 次 build：counter 需从 1 走到 1001（每次 _next_seq 都被调用）
        build_dest_filename(stem_dt, ".jpg", tmp_path, False, taken)
        # 此时 counter 已递增到 1001
        # 下一次 _next_seq 返回 1002
        next_n = _next_seq()
        assert next_n == 1002, f"expected 1002, got {next_n}"

    def test_reset_counter_works(self, tmp_path):
        """reset_counter 后应从 1 重新开始"""
        build_dest_filename(datetime(2024, 1, 1, 12, 0, 0), ".jpg", tmp_path, False, set())
        build_dest_filename(datetime(2024, 1, 1, 12, 0, 0), ".jpg", tmp_path, False, set())
        assert _next_seq() == 3

        reset_counter()
        assert _next_seq() == 1


class TestLockExported:
    """确保锁对象被正确导出（其他模块可能用得到）"""

    def test_filename_lock_is_threading_lock(self):
        """_filename_lock 应该是 threading.Lock 实例"""
        assert isinstance(_filename_lock, type(threading.Lock()))
