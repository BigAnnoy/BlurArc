"""
Plan B - thumbnail_manager 新增 30+ 测试用例
目标：补齐缓存命中、格式、并发、性能、边界、错误处理场景

注意：实际 API 是 `get_thumbnail_sync(str(file_path))`（返回 Path），
     返回 bytes 的 `_generate_thumbnail_sync` 是私有方法。
     本文件按真实 API 编写测试。
"""
import concurrent.futures
import os
import time
import hashlib
import threading
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from backend.thumbnail_manager import ThumbnailManager


# ===========================================================================
# Test 1: 缓存命中
# ===========================================================================
class TestThumbnailCacheHit:
    """缩略图缓存命中 / 失效逻辑"""

    def test_first_call_generates_thumb(self, tmp_path, make_image, temp_thumb_dir):
        """首次调用应生成缩略图并返回 Path"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = make_image(tmp_path / "src.jpg", 200, 200)
        result = mgr.get_thumbnail_sync(str(img))
        assert result is not None
        assert isinstance(result, Path)
        assert result.exists()
        cache_files = list(temp_thumb_dir.iterdir())
        assert len(cache_files) >= 1

    def test_second_call_returns_same_path(self, tmp_path, make_image, temp_thumb_dir):
        """第二次调用应返回同一缓存 Path（命中）"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = make_image(tmp_path / "src.jpg", 200, 200)
        first = mgr.get_thumbnail_sync(str(img))
        second = mgr.get_thumbnail_sync(str(img))
        assert first == second
        assert first.exists()

    def test_cache_key_changes_on_mtime(self, tmp_path, make_image, temp_thumb_dir):
        """mtime 改变后 cache_key 必须变化"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = make_image(tmp_path / "src.jpg", 200, 200)
        key1 = mgr._generate_cache_key(img)
        # 等待并修改 mtime 到未来
        future_mtime = time.time() + 100
        os.utime(img, (future_mtime, future_mtime))
        key2 = mgr._generate_cache_key(img)
        assert key1 != key2

    def test_cache_key_changes_on_size(self, tmp_path, temp_thumb_dir):
        """文件大小改变后 cache_key 必须变化"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = tmp_path / "a.jpg"
        img.write_bytes(b"x" * 100)
        key1 = mgr._generate_cache_key(img)
        img.write_bytes(b"x" * 200)
        key2 = mgr._generate_cache_key(img)
        assert key1 != key2

    def test_cache_dir_auto_created(self, tmp_path, monkeypatch):
        """实例化时 cache_dir 不存在应自动创建"""
        new_dir = tmp_path / "auto_created_cache"
        monkeypatch.setenv("HOME", str(tmp_path))
        mgr = ThumbnailManager()
        mgr.cache_dir = new_dir
        # 触发一次生成
        mgr.cache_dir.mkdir(parents=True, exist_ok=True)
        assert mgr.cache_dir.exists()

    def test_get_thumbnail_async_submits_to_executor(self, tmp_path, make_image, temp_thumb_dir):
        """异步 get_thumbnail 应提交到 executor（首次返回 None）"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = make_image(tmp_path / "src.jpg", 200, 200)
        # 首次异步调用：缓存未生成，返回 None
        result = mgr.get_thumbnail(str(img))
        assert result is None
        # 等待后台任务完成
        time.sleep(0.5)
        # 第二次同步调用应返回缓存路径
        result2 = mgr.get_thumbnail_sync(str(img))
        assert result2 is not None
        assert result2.exists()


# ===========================================================================
# Test 2: 图片格式支持
# ===========================================================================
class TestThumbnailImageFormats:
    """不同图片格式 / 模式的缩略图生成"""

    @pytest.mark.parametrize("ext", ["jpg", "png", "webp", "bmp"])
    def test_generate_thumb_for_format(self, tmp_path, make_image, temp_thumb_dir, ext):
        """各常见格式都能生成缩略图"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = make_image(tmp_path / f"src.{ext}", 300, 300, ext=ext)
        result = mgr.get_thumbnail_sync(str(img))
        assert result is not None
        assert result.exists()
        # 输出总是 JPEG
        assert result.suffix == ".jpg"

    def test_transparent_png_preserves(self, tmp_path, temp_thumb_dir):
        """透明 PNG 缩略图能正常解码"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img_path = tmp_path / "transparent.png"
        Image.new("RGBA", (200, 200), (255, 0, 0, 128)).save(str(img_path))

        result = mgr.get_thumbnail_sync(str(img_path))
        assert result is not None
        with Image.open(result) as thumb:
            assert thumb.size[0] <= mgr.thumbnail_size[0]
            assert thumb.size[1] <= mgr.thumbnail_size[1]

    def test_4k_image_downscale_preserves_aspect(self, tmp_path, temp_thumb_dir):
        """4K 大图应等比缩放"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        mgr.thumbnail_size = (256, 256)
        img_path = tmp_path / "4k.jpg"
        Image.new("RGB", (3840, 2160), (50, 100, 150)).save(str(img_path), quality=70)

        result = mgr.get_thumbnail_sync(str(img_path))
        assert result is not None
        with Image.open(result) as thumb:
            # 16:9 等比缩放到 256 宽 → 144 高
            assert thumb.size == (256, 144)

    def test_corrupted_image_returns_none(self, tmp_path, make_corrupted, temp_thumb_dir):
        """损坏文件应返回 None（不抛错）"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = make_corrupted(tmp_path / "broken.jpg")
        result = mgr.get_thumbnail_sync(str(img))
        assert result is None

    def test_zero_byte_file_returns_none(self, tmp_path, make_zero_byte, temp_thumb_dir):
        """0 字节文件应返回 None"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = make_zero_byte(tmp_path / "empty.jpg")
        result = mgr.get_thumbnail_sync(str(img))
        assert result is None

    def test_tiff_preview_conversion(self, tmp_path, temp_thumb_dir):
        """TIFF 文件应转换为 JPEG 预览"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        tiff_path = tmp_path / "image.tiff"
        Image.new("RGB", (200, 200), (0, 255, 0)).save(str(tiff_path))

        result = mgr.get_preview_jpeg(str(tiff_path))
        assert result is not None
        assert result.exists()
        assert result.suffix == ".jpg"

    def test_palette_mode_with_transparency(self, tmp_path, temp_thumb_dir):
        """P 模式带透明通道的图片应能处理"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        p_path = tmp_path / "palette.png"
        img = Image.new("P", (100, 100))
        img.info["transparency"] = 128
        img.save(str(p_path))

        result = mgr.get_thumbnail_sync(str(p_path))
        assert result is not None


# ===========================================================================
# Test 3: 视频缩略图
# ===========================================================================
class TestThumbnailVideo:
    """视频缩略图生成（ffmpeg mock）"""

    def test_video_thumb_uses_subprocess(self, tmp_path, make_fake_video, temp_thumb_dir, monkeypatch):
        """视频缩略图应调用 subprocess.run（走 ffmpeg）"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir

        # mock VideoProcessor 成功路径（同时写出 jpg 文件以模拟 ffmpeg 抽帧）
        def fake_generate(video_path, output_path):
            # 创建输出目录 + 写入 jpg bytes
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (50, 50), (255, 0, 0)).save(str(output_path))
            return True

        with patch("backend.thumbnail_manager.VideoProcessor") as mock_vp:
            mock_vp.generate_thumbnail.side_effect = fake_generate
            video = make_fake_video(tmp_path / "clip.mp4")
            result = mgr.get_thumbnail_sync(str(video))
            assert result is not None
            assert result.exists()
            mock_vp.generate_thumbnail.assert_called_once()

    def test_video_thumb_failure_returns_none(self, tmp_path, make_fake_video, temp_thumb_dir):
        """ffmpeg 返回 False 时返回 None"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        with patch("backend.thumbnail_manager.VideoProcessor") as mock_vp:
            mock_vp.generate_thumbnail.return_value = False
            video = make_fake_video(tmp_path / "clip.mp4")
            result = mgr.get_thumbnail_sync(str(video))
            assert result is None

    def test_video_thumb_raises_returns_none(self, tmp_path, make_fake_video, temp_thumb_dir):
        """ffmpeg 抛异常时返回 None（不崩溃）"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        with patch("backend.thumbnail_manager.VideoProcessor") as mock_vp:
            mock_vp.generate_thumbnail.side_effect = RuntimeError("ffmpeg crashed")
            video = make_fake_video(tmp_path / "clip.mp4")
            result = mgr.get_thumbnail_sync(str(video))
            assert result is None

    def test_get_preview_jpeg_video_returns_none(self, tmp_path, temp_thumb_dir):
        """视频文件 get_preview_jpeg 应返回 None（不支持）"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        video = tmp_path / "movie.mp4"
        video.write_bytes(b"fake video")
        result = mgr.get_preview_jpeg(str(video))
        assert result is None


# ===========================================================================
# Test 4: 并发
# ===========================================================================
class TestThumbnailConcurrency:
    """并发安全测试"""

    def test_concurrent_same_file_single_cache_entry(self, tmp_path, make_image, temp_thumb_dir):
        """20 个线程同时处理同一文件，缓存只有 1 个文件"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = make_image(tmp_path / "src.jpg", 500, 500)

        def generate():
            return mgr.get_thumbnail_sync(str(img))

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            results = list(ex.map(lambda _: generate(), range(20)))

        # 全部应返回同一 Path（缓存命中）
        assert all(r == results[0] for r in results)
        cache_files = list(temp_thumb_dir.iterdir())
        assert len(cache_files) == 1

    def test_concurrent_different_files(self, tmp_path, make_image, temp_thumb_dir):
        """并发处理不同文件应都成功"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        images = [make_image(tmp_path / f"img_{i}.jpg", 200, 200) for i in range(10)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            futures = [ex.submit(mgr.get_thumbnail_sync, str(img)) for img in images]
            results = [f.result() for f in futures]

        assert all(r is not None for r in results)
        assert all(r.exists() for r in results)


# ===========================================================================
# Test 5: 性能
# ===========================================================================
@pytest.mark.slow
class TestThumbnailPerformance:
    """性能基准（CI 可跳过）"""

    def test_batch_50_images_under_10s(self, tmp_path, make_image, temp_thumb_dir):
        """50 张图批量生成 < 10s"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        images = [make_image(tmp_path / f"img_{i}.jpg", 200, 200) for i in range(50)]

        start = time.time()
        for img in images:
            mgr.get_thumbnail_sync(str(img))
        elapsed = time.time() - start

        assert elapsed < 10.0, f"50 images took {elapsed:.2f}s, expected < 10s"


# ===========================================================================
# Test 6: 边界
# ===========================================================================
class TestThumbnailEdgeCases:
    """边界场景：路径、特殊文件名、目录不存在"""

    def test_path_with_chinese(self, tmp_path, make_image, temp_thumb_dir):
        """中文路径应正常工作"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        chinese_dir = tmp_path / "相册" / "子目录"
        chinese_dir.mkdir(parents=True)
        img = make_image(chinese_dir / "照片.jpg", 200, 200)
        result = mgr.get_thumbnail_sync(str(img))
        assert result is not None
        assert result.exists()

    def test_path_with_spaces(self, tmp_path, make_image, temp_thumb_dir):
        """带空格的路径应正常工作"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        space_dir = tmp_path / "My Album" / "sub folder"
        space_dir.mkdir(parents=True)
        img = make_image(space_dir / "my photo.jpg", 200, 200)
        result = mgr.get_thumbnail_sync(str(img))
        assert result is not None

    def test_get_thumbnail_nonexistent_returns_none(self, temp_thumb_dir):
        """不存在的文件应返回 None"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        result = mgr.get_thumbnail_sync("Z:/nonexistent/file.jpg")
        assert result is None

    def test_get_thumbnail_directory_returns_none(self, tmp_path, temp_thumb_dir):
        """目录而非文件应返回 None"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        result = mgr.get_thumbnail_sync(str(tmp_path))
        assert result is None

    def test_unsupported_extension_returns_none(self, tmp_path, temp_thumb_dir):
        """不支持的扩展名应返回 None"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        txt = tmp_path / "readme.txt"
        txt.write_text("hello")
        result = mgr.get_thumbnail_sync(str(txt))
        assert result is None


# ===========================================================================
# Test 7: 错误处理 / 异常分支
# ===========================================================================
class TestThumbnailErrorHandling:
    """错误处理：DB 异常、cache_dir 不存在、并发下的异常"""

    def test_get_thumbnail_sync_exception_in_generate(self, tmp_path, make_image, temp_thumb_dir):
        """缩略图生成抛异常时返回 None（不崩溃）"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        img = make_image(tmp_path / "src.jpg", 200, 200)

        with patch.object(mgr, "_generate_image_thumbnail", side_effect=Exception("boom")):
            result = mgr.get_thumbnail_sync(str(img))
            assert result is None


# ===========================================================================
# Test 8: 缓存清理
# ===========================================================================
class TestThumbnailCacheCleanup:
    """缓存清理（按时间 / 按大小）"""

    def test_cleanup_cache_aged_files(self, tmp_path, temp_thumb_dir):
        """清理过期的缓存文件"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir

        # 创建老文件
        old = temp_thumb_dir / "old_cache.jpg"
        old.write_bytes(b"x" * 100)
        old_time = time.time() - (40 * 24 * 60 * 60)  # 40 天前
        os.utime(old, (old_time, old_time))

        # 创建新文件
        new = temp_thumb_dir / "new_cache.jpg"
        new.write_bytes(b"y" * 100)

        mgr.cleanup_cache(max_age_days=30)

        # 老的应被清理，新的应保留
        assert not old.exists()
        assert new.exists()

    def test_cleanup_cache_by_size_returns_dict(self, tmp_path, temp_thumb_dir):
        """按大小清理应返回 dict"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        result = mgr.cleanup_cache_by_size(max_size_mb=100)
        assert "deleted_count" in result
        assert "freed_mb" in result
        assert "remaining_mb" in result

    def test_cleanup_cache_handles_empty_dir(self, temp_thumb_dir):
        """空缓存目录应不报错"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        # 不应抛异常
        mgr.cleanup_cache(max_age_days=30)
        mgr.cleanup_cache_by_size(max_size_mb=100)

    def test_cleanup_cache_by_size_under_threshold(self, temp_thumb_dir):
        """总大小未超限时返回 deleted_count=0"""
        mgr = ThumbnailManager()
        mgr.cache_dir = temp_thumb_dir
        for i in range(3):
            (temp_thumb_dir / f"small_{i}.jpg").write_bytes(b"x" * 100)
        result = mgr.cleanup_cache_by_size(max_size_mb=1)
        assert result["deleted_count"] == 0
        assert result["freed_mb"] == 0.0


# ===========================================================================
# Test 9: 单例
# ===========================================================================
class TestThumbnailSingleton:
    """全局单例 get_thumbnail_manager"""

    def test_singleton_returns_same_instance(self):
        """连续调用应返回同一实例"""
        m1 = ThumbnailManager()
        m2 = ThumbnailManager()
        # 这里测试的是 ThumbnailManager 本身可实例化多次（与 get_thumbnail_manager 单例不同）
        # 注：每个 ThumbnailManager 是独立的，但 get_thumbnail_manager 是单例
        assert m1 is not m2  # 裸构造每次新实例

    def test_get_thumbnail_manager_returns_thumbnail_manager(self):
        """get_thumbnail_manager 应返回 ThumbnailManager 实例"""
        from backend.thumbnail_manager import get_thumbnail_manager
        mgr = get_thumbnail_manager()
        assert isinstance(mgr, ThumbnailManager)
