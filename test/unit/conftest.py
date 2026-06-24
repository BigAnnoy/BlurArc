"""
thumbnail_manager 测试共享 fixture
Plan B 配套：提供测试图、损坏文件、mock ffmpeg、隔离缩略图目录

注意：此文件使用 pytest auto-discovery（conftest.py 在每个 test 目录自动加载），
     让 unit 目录下所有测试都能直接引用 make_image / temp_thumb_dir 等 fixture。
"""
import os
from pathlib import Path
from typing import Optional

import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# 工厂函数（可在测试体内直接调用）
# ---------------------------------------------------------------------------

def create_test_image(
    path: Path,
    width: int = 100,
    height: int = 100,
    color: tuple = (100, 150, 200),
    ext: str = "jpg",
    exif_rotation: Optional[int] = None,
) -> Path:
    """创建带可选 EXIF 旋转的测试图"""
    img = Image.new("RGB", (width, height), color=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 让 Pillow 通过文件后缀自动选编码器（jpg -> JPEG, tif -> TIFF）
    img.save(str(path))
    return path


def create_corrupted_image(path: Path) -> Path:
    """截断的 JPEG（前 100 字节后截断）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 96)
    return path


def create_zero_byte_file(path: Path) -> Path:
    """0 字节文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def create_fake_video(path: Path) -> Path:
    """模拟视频文件（带 mp4 magic bytes）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00\x00\x00\x20ftypmp42" + b"\x00" * 100)
    return path


# ---------------------------------------------------------------------------
# pytest fixture：返回工厂函数
# ---------------------------------------------------------------------------

@pytest.fixture
def make_image():
    """工厂 fixture：测试图"""
    return create_test_image


@pytest.fixture
def make_corrupted():
    """工厂 fixture：损坏文件"""
    return create_corrupted_image


@pytest.fixture
def make_zero_byte():
    """工厂 fixture：0 字节"""
    return create_zero_byte_file


@pytest.fixture
def make_fake_video():
    """工厂 fixture：假视频"""
    return create_fake_video


# ---------------------------------------------------------------------------
# mock fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ffmpeg(monkeypatch):
    """mock subprocess.run 给 ffmpeg 调用"""
    class FakeResult:
        returncode = 0
        stdout = b"FAKE_VIDEO_FRAME_BYTES" * 100
        stderr = b""

    def fake_run(*args, **kwargs):
        return FakeResult()

    monkeypatch.setattr("subprocess.run", fake_run)
    return fake_run


@pytest.fixture
def mock_ffmpeg_missing(monkeypatch):
    """模拟 ffmpeg 不存在的场景"""
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ffmpeg not found")

    monkeypatch.setattr("subprocess.run", fake_run)
    return fake_run


# ---------------------------------------------------------------------------
# 隔离缩略图目录
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_thumb_dir(tmp_path, monkeypatch):
    """隔离的缩略图目录（不污染 ~/.photomanager）"""
    thumb_dir = tmp_path / "thumbnails"
    thumb_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    return thumb_dir
