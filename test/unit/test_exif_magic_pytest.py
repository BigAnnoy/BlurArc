"""_has_exif_magic 专项测试

覆盖 EXIF magic bytes 优化的所有路径：
- 各种已知图片格式（JPEG/PNG/WebP/TIFF）
- 已知非图片格式（ZIP/PDF/纯文本）
- 边界条件（空文件、短文件、不存在文件）
- 集成测试：真实 PIL 生成的 JPEG/PNG 应通过 magic check
"""
import pytest
from pathlib import Path

from backend.import_manager import _has_exif_magic, EXIF_SUPPORTED_MAGIC


class TestExifMagicBytes:
    """magic bytes 白名单测试"""

    @pytest.mark.parametrize("magic,expected", [
        # JPEG 常见变体（全部应通过）
        (b'\xff\xd8\xff\xe0', True),   # JPEG/JFIF
        (b'\xff\xd8\xff\xe1', True),   # JPEG/Exif
        (b'\xff\xd8\xff\xdb', True),   # JPEG/raw
        (b'\xff\xd8\xff\xee', True),   # JPEG/Adobe
        # 其他已知格式
        (b'\x89PNG\r\n', True),        # PNG
        (b'RIFF\x00\x00\x00\x00WEBP', True),  # WebP (RIFF 容器)
        (b'II*\x00', True),            # TIFF little-endian
        (b'MM\x00*', True),            # TIFF big-endian
        # 非图片格式（应被拒绝）
        (b'NOT_MAGIC', False),
        (b'PK\x03\x04', False),        # ZIP
        (b'%PDF', False),              # PDF
        (b'GIF89a', False),            # GIF（不在白名单，目前未支持）
        # 边界
        (b'', False),                  # empty
        (b'\x00', False),              # 单字节
    ])
    def test_magic_detection(self, tmp_path, magic, expected):
        """_has_exif_magic 应对各种 magic bytes 给出正确判断"""
        f = tmp_path / "test"
        f.write_bytes(magic + b"\x00" * 100)
        assert _has_exif_magic(f) is expected, \
            f"magic {magic!r}: 期望 {expected}, 实际 {_has_exif_magic(f)}"

    def test_jpeg_with_exif_date_found(self, tmp_path):
        """有 EXIF 的 JPEG 应通过 magic check"""
        from PIL import Image
        import piexif

        img_path = tmp_path / "with_exif.jpg"
        img = Image.new("RGB", (100, 100))
        exif_dict = {
            "0th": {},
            "Exif": {piexif.ExifIFD.DateTimeOriginal: b"2023:05:15 14:30:00"},
            "GPS": {},
            "1st": {},
            "thumbnail": None,
        }
        exif_bytes = piexif.dump(exif_dict)
        img.save(str(img_path), exif=exif_bytes)
        assert _has_exif_magic(img_path) is True

    def test_png_passes_magic(self, tmp_path):
        """PNG 应通过 magic check（即使无 EXIF）"""
        from PIL import Image
        img_path = tmp_path / "test.png"
        Image.new("RGB", (100, 100)).save(str(img_path))
        assert _has_exif_magic(img_path) is True

    def test_webp_passes_magic(self, tmp_path):
        """WebP 应通过 magic check（RIFF 容器）"""
        from PIL import Image
        img = Image.new("RGB", (100, 100))
        webp_path = tmp_path / "test.webp"
        try:
            img.save(str(webp_path), format="WEBP")
        except Exception:
            pytest.skip("PIL WebP encoder not available")
        assert _has_exif_magic(webp_path) is True

    def test_text_file_rejected(self, tmp_path):
        """文本文件应被拒绝"""
        f = tmp_path / "test.txt"
        f.write_text("not an image")
        assert _has_exif_magic(f) is False

    def test_nonexistent_file_returns_false(self, tmp_path):
        """不存在文件不应抛错"""
        f = tmp_path / "nonexistent.jpg"
        assert _has_exif_magic(f) is False

    def test_short_file_returns_false(self, tmp_path):
        """< 4 字节文件返回 False（无法匹配任何 4 字节签名）"""
        f = tmp_path / "short.jpg"
        f.write_bytes(b"\xff")  # 1 字节
        assert _has_exif_magic(f) is False

        f2 = tmp_path / "short3.bin"
        f2.write_bytes(b"\xff\xd8\xff")  # 3 字节
        assert _has_exif_magic(f2) is False

    def test_directory_returns_false(self, tmp_path):
        """目录路径返回 False（open 会抛 IsADirectoryError，被 OSError 捕获）"""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        assert _has_exif_magic(subdir) is False

    def test_constant_covers_known_formats(self):
        """白名单应包含所有支持的格式"""
        # HEIC: 00 00 00 ?? 66 74 79 70 68 65 69 63 — 不一致，留给后续
        assert b'\xff\xd8\xff\xe0' in EXIF_SUPPORTED_MAGIC  # JPEG/JFIF
        assert b'\xff\xd8\xff\xe1' in EXIF_SUPPORTED_MAGIC  # JPEG/Exif
        assert b'\x89PNG' in EXIF_SUPPORTED_MAGIC            # PNG
        assert b'RIFF' in EXIF_SUPPORTED_MAGIC               # WebP
        assert b'II*\x00' in EXIF_SUPPORTED_MAGIC            # TIFF-LE
        assert b'MM\x00*' in EXIF_SUPPORTED_MAGIC            # TIFF-BE

    def test_constant_is_frozenset(self):
        """EXIF_SUPPORTED_MAGIC 必须是 frozenset（O(1) 查找 + 不可变）"""
        assert isinstance(EXIF_SUPPORTED_MAGIC, frozenset)


class TestExifMagicIntegration:
    """与 _get_media_date 的集成测试"""

    def test_text_file_skips_pil_via_magic_check(self, tmp_path, monkeypatch):
        """文本文件：_get_media_date 应走 mtime fallback，不调用 PIL

        验证优化 4 的核心收益：避免对非图片文件调用 PIL.Image.open()
        """
        from backend.import_manager import ImportManager
        import datetime

        manager = ImportManager()
        text_file = tmp_path / "notes.txt"
        text_file.write_text("not an image, just text content")
        # 设置 mtime 到 2024-06-01
        target_mtime = datetime.datetime(2024, 6, 1, 12, 0, 0)
        import os
        os.utime(text_file, (target_mtime.timestamp(), target_mtime.timestamp()))

        # 监视 PIL.Image.open 是否被调用
        from PIL import Image
        original_open = Image.open
        pil_open_called = [False]

        def tracking_open(*args, **kwargs):
            pil_open_called[0] = True
            return original_open(*args, **kwargs)

        monkeypatch.setattr("PIL.Image.open", tracking_open)

        # 调用 _get_media_date
        result = manager._get_media_date(text_file)

        # 关键断言：PIL.Image.open 不应被调用
        assert pil_open_called[0] is False, \
            "PIL.Image.open 被调用了，magic check 未生效"
        # 应返回 mtime
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 1

    def test_pdf_skips_pil_via_magic_check(self, tmp_path, monkeypatch):
        """PDF 文件：_get_media_date 应走 mtime fallback，不调用 PIL"""
        from backend.import_manager import ImportManager
        import datetime

        manager = ImportManager()
        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%fake pdf content" + b"\x00" * 100)
        target_mtime = datetime.datetime(2023, 12, 25, 10, 0, 0)
        import os
        os.utime(pdf_file, (target_mtime.timestamp(), target_mtime.timestamp()))

        from PIL import Image
        original_open = Image.open
        pil_open_called = [False]

        def tracking_open(*args, **kwargs):
            pil_open_called[0] = True
            return original_open(*args, **kwargs)

        monkeypatch.setattr("PIL.Image.open", tracking_open)

        result = manager._get_media_date(pdf_file)
        assert pil_open_called[0] is False
        assert result is not None
        assert result.year == 2023

    def test_zip_file_skips_pil_via_magic_check(self, tmp_path, monkeypatch):
        """ZIP 文件：_get_media_date 应走 mtime fallback"""
        from backend.import_manager import ImportManager

        manager = ImportManager()
        zip_file = tmp_path / "archive.zip"
        # 真实 ZIP magic
        zip_file.write_bytes(b"PK\x03\x04" + b"\x00" * 100)

        from PIL import Image
        original_open = Image.open
        pil_open_called = [False]

        def tracking_open(*args, **kwargs):
            pil_open_called[0] = True
            return original_open(*args, **kwargs)

        monkeypatch.setattr("PIL.Image.open", tracking_open)

        result = manager._get_media_date(zip_file)
        assert pil_open_called[0] is False
        assert result is not None
