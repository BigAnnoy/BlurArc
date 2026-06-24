"""
API 测试共享 fixture
- 每个测试用临时目录隔离（HOME / 配置目录）
- 复用 backend.api_server 模块级 Flask app
- 提供 sample_album / populated_db 等业务 fixture
"""
import os
import shutil
import pytest
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Werkzeug 兼容补丁：Werkzeug 3.x 移除了 __version__，Flask 2.3 test_client 还在用
# 预存在环境问题：pip 装的是 Werkzeug 3.1.3，Flask 2.3.0 需要 werkzeug.__version__
# 这里手动注入一个版本字符串，让 app.test_client() 能正常构造
# ---------------------------------------------------------------------------
import werkzeug
if not hasattr(werkzeug, "__version__"):
    try:
        from importlib.metadata import version as _pkg_version
        werkzeug.__version__ = _pkg_version("werkzeug")
    except Exception:
        werkzeug.__version__ = "3.0.0"


# ---------------------------------------------------------------------------
# 环境隔离：每个测试用 tmp_path 隔离 HOME/缩略图/配置，避免污染 ~/.photomanager
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def isolate_environment(tmp_path, monkeypatch):
    """每个测试用临时目录隔离

    1. 重定向 HOME → tmp_path（缩略图缓存 ~/.photomanager 在这之下）
    2. 保证 config 目录存在（数据库自动建表在 .config/photo_manager.db）
    """
    # 缩略图缓存 ~/.photomanager/thumbnails/ 在 home 之下，重定向 HOME
    monkeypatch.setenv("HOME", str(tmp_path))
    # 确保 home 目录存在（部分平台 HOME 可能未自动创建）
    (tmp_path / ".photomanager").mkdir(exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Flask app / client fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def app():
    """复用 backend.api_server 模块级 app（api_server 没有 create_app 工厂）"""
    from backend.api_server import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# 业务 fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_album(tmp_path):
    """含 10 张测试图的相册（用于 API 文件/导入测试）"""
    from PIL import Image
    album = tmp_path / "sample_album"
    album.mkdir()
    for i in range(10):
        img = Image.new("RGB", (200, 200), (i * 25, 100, 200))
        img.save(album / f"sample_{i:02d}.jpg", quality=85)
    return album


@pytest.fixture
def populated_db():
    """含 5 张 photo 记录的数据库（直接写入 api_server 用的真实 DB）

    警告：使用真实 DB（init_db 已建表）。测试结束后清理本 fixture 写入的记录。
    """
    from backend.database import init_db, SessionLocal, Photo
    from datetime import datetime

    init_db()
    session = SessionLocal()
    inserted_ids = []
    try:
        for i in range(5):
            p = Photo(
                filename=f"photo_{i}.jpg",
                path=f"/fake/photo_{i}.jpg",
                size=1000 + i,
                md5_hash=f"md5_{i:032x}",
                created_at=datetime(2024, 1, i + 1),
                modified_at=datetime(2024, 1, i + 1),
                media_date=datetime(2024, 1, i + 1),
                file_type="photo",
                extension=".jpg",
                imported_at=datetime(2024, 1, i + 1),
            )
            session.add(p)
        session.commit()
        # 记录刚插入的 id（用于 teardown）
        inserted_ids = [
            p.id for p in session.query(Photo).filter(Photo.path.like("/fake/photo_%")).all()
        ]
    finally:
        session.close()

    yield inserted_ids

    # teardown：清理 fixture 插入的 fake 记录
    cleanup = SessionLocal()
    try:
        cleanup.query(Photo).filter(Photo.path.like("/fake/photo_%")).delete(synchronize_session=False)
        cleanup.commit()
    finally:
        cleanup.close()
