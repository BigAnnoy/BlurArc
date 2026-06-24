"""
测试 _scan_source 的性能优化（优化 1+2）

优化 1：scan 时一并采集 size（用 os.scandir + stat_result）
优化 2：扩展名 O(1) 查找（frozenset + os.path.splitext）

行为不变：返回的 list 元素应仍是 Path 对象（向后兼容）
"""
import os
import pytest
from pathlib import Path
from PIL import Image

from backend.import_manager import ImportManager


@pytest.fixture
def manager():
    return ImportManager()


@pytest.fixture
def album_with_media(tmp_path):
    """含 5 张图 + 2 个非媒体文件的临时相册"""
    album = tmp_path / "album"
    album.mkdir()
    for i, ext in enumerate(["jpg", "png", "webp", "jpg", "png"]):
        img = Image.new("RGB", (50, 50), color=(i * 30, 100, 200))
        img.save(album / f"img_{i}.{ext}")
    # 2 个非媒体文件（应被过滤）
    (album / "notes.txt").write_text("not media")
    (album / "data.json").write_text("{}")
    return album


class TestScanSourceReturnsPaths:
    """契约：返回的必须是 Path 列表（向后兼容）"""

    def test_returns_list_of_paths(self, manager, album_with_media):
        result = manager._scan_source(album_with_media, ignore_last_scan=True)
        assert isinstance(result, list)
        assert all(isinstance(p, Path) for p in result), \
            f"Expected all Path objects, got types: {[type(p).__name__ for p in result]}"

    def test_finds_all_media_files(self, manager, album_with_media):
        result = manager._scan_source(album_with_media, ignore_last_scan=True)
        assert len(result) == 5, f"Expected 5 media files, got {len(result)}"

    def test_filters_non_media(self, manager, album_with_media):
        result = manager._scan_source(album_with_media, ignore_last_scan=True)
        names = {p.name for p in result}
        assert "notes.txt" not in names
        assert "data.json" not in names

    def test_recursive_scan(self, manager, tmp_path):
        """子目录中的媒体也应被找到"""
        album = tmp_path / "album"
        album.mkdir()
        sub = album / "subfolder"
        sub.mkdir()
        Image.new("RGB", (30, 30)).save(sub / "deep.jpg")
        Image.new("RGB", (30, 30)).save(album / "top.jpg")
        result = manager._scan_source(album, ignore_last_scan=True)
        names = {p.name for p in result}
        assert names == {"deep.jpg", "top.jpg"}


class TestScanSourcePerformance:
    """性能基准：1000 文件 scan 应 < 2 秒"""

    def test_scan_1000_files_under_2s(self, manager, tmp_path):
        import time
        album = tmp_path / "big_album"
        album.mkdir()
        for i in range(1000):
            img = Image.new("RGB", (50, 50), color=(i % 255, 100, 200))
            img.save(album / f"img_{i}.jpg")

        start = time.time()
        result = manager._scan_source(album, ignore_last_scan=True)
        elapsed = time.time() - start

        assert len(result) == 1000
        assert elapsed < 2.0, f"Scan took {elapsed:.2f}s, expected < 2.0s"

    def test_scan_size_collected_per_file(self, manager, tmp_path):
        """每个返回的 Path 都能成功 stat()（验证文件可访问）"""
        album = tmp_path / "album"
        album.mkdir()
        for i in range(10):
            img = Image.new("RGB", (50, 50))
            img.save(album / f"img_{i}.jpg")

        result = manager._scan_source(album, ignore_last_scan=True)
        for p in result:
            # 不抛错即可
            size = p.stat().st_size
            assert size > 0
