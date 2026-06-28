"""
ConfigManager pytest 单元测试
测试配置管理模块的所有公共 API 方法
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config_manager import ConfigManager
from backend.database import SessionLocal, Setting, Photo, Album, AlbumPhoto, ImportHistory, Base, engine


@pytest.fixture
def temp_dir():
    """创建临时目录，测试后自动清理"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def db_cleanup():
    """清理数据库fixture"""
    def cleanup():
        db = SessionLocal()
        try:
            db.query(ImportHistory).delete()
            db.query(Photo).delete()
            db.query(Setting).delete()
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    
    cleanup()
    yield
    cleanup()


def create_config_manager_with_mock(temp_config_dir):
    """创建带有模拟属性的ConfigManager实例"""
    mock_config_dir = MagicMock()
    mock_config_dir.__get__ = MagicMock(return_value=Path(temp_config_dir))
    
    mock_config_file = MagicMock()
    mock_config_file.__get__ = MagicMock(return_value=Path(temp_config_dir) / "config.json")
    
    with patch.object(ConfigManager, 'CONFIG_DIR', mock_config_dir), \
         patch.object(ConfigManager, 'CONFIG_FILE', mock_config_file):
        
        config_manager = ConfigManager()
        return config_manager


@pytest.fixture
def in_memory_db(monkeypatch):
    """创建内存 SQLite，注入到 config_manager/database 的 SessionLocal，teardown 时还原。
    使用 StaticPool + check_same_thread=False 让多线程共享同一连接。"""
    from backend import database as db_mod
    from backend import config_manager as cm_mod

    original_engine = db_mod.engine
    original_session_local = db_mod.SessionLocal
    original_cm_session = cm_mod.SessionLocal

    test_engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    monkeypatch.setattr(db_mod, "engine", test_engine)
    monkeypatch.setattr(db_mod, "SessionLocal", TestSession)
    monkeypatch.setattr(cm_mod, "SessionLocal", TestSession)

    yield TestSession

    monkeypatch.setattr(db_mod, "engine", original_engine)
    monkeypatch.setattr(db_mod, "SessionLocal", original_session_local)
    monkeypatch.setattr(cm_mod, "SessionLocal", original_cm_session)
    test_engine.dispose()


def test_initialization(temp_dir):
    """测试初始化配置"""
    mock_config_dir = MagicMock()
    mock_config_dir.__get__ = MagicMock(return_value=Path(temp_dir))
    
    mock_config_file = MagicMock()
    mock_config_file.__get__ = MagicMock(return_value=Path(temp_dir) / "config.json")
    
    with patch.object(ConfigManager, 'CONFIG_DIR', mock_config_dir), \
         patch.object(ConfigManager, 'CONFIG_FILE', mock_config_file):
        
        config_manager = ConfigManager()
        
        default_config = config_manager._default_config()
        assert config_manager.config == default_config
        
        assert Path(temp_dir).exists()
        
        with tempfile.TemporaryDirectory() as temp_album_dir:
            config_manager.set_album_path(temp_album_dir)
            assert (Path(temp_dir) / "config.json").exists()


def test_is_first_run(temp_dir):
    """测试首次运行检测"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    assert config_manager.is_first_run()
    
    with tempfile.TemporaryDirectory() as temp_album_dir:
        config_manager.set_album_path(temp_album_dir)
        assert not config_manager.is_first_run()


def test_set_album_path_valid(temp_dir):
    """测试设置有效的相册路径"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    with tempfile.TemporaryDirectory() as temp_album_dir:
        result = config_manager.set_album_path(temp_album_dir)
        assert result
        
        expected_path = str(Path(temp_album_dir).absolute())
        assert config_manager.get_album_path() == expected_path
        
        assert config_manager.config.get("created_at") is not None


def test_set_album_path_invalid_nonexistent(temp_dir):
    """测试设置不存在的相册路径"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    nonexistent_path = str(Path(temp_dir) / "nonexistent")
    result = config_manager.set_album_path(nonexistent_path)
    assert not result


def test_get_album_path(temp_dir):
    """测试获取相册路径"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    assert config_manager.get_album_path() is None
    
    with tempfile.TemporaryDirectory() as temp_album_dir:
        config_manager.set_album_path(temp_album_dir)
        expected_path = str(Path(temp_album_dir).absolute())
        assert config_manager.get_album_path() == expected_path


def test_set_last_import(temp_dir):
    """测试更新最后导入时间"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    custom_timestamp = "2023-01-01T12:00:00"
    config_manager.set_last_import(custom_timestamp)
    assert config_manager.get_last_import() == custom_timestamp
    
    config_manager.set_last_import(None)
    last_import = config_manager.get_last_import()
    assert last_import is not None
    datetime.fromisoformat(last_import)


def test_update_setting(temp_dir):
    """测试更新应用设置"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    config_manager.update_setting("import_mode_default", "move")
    assert config_manager.get_setting("import_mode_default") == "move"
    
    config_manager.update_setting("new_setting", "new_value")
    assert config_manager.get_setting("new_setting") == "new_value"


def test_get_setting(temp_dir):
    """测试获取应用设置"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    assert config_manager.get_setting("nonexistent_setting", "default_value") == "default_value"
    
    config_manager.update_setting("test_setting", "test_value")
    assert config_manager.get_setting("test_setting") == "test_value"


def test_get_all_config(temp_dir):
    """测试获取所有配置"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    all_config = config_manager.get_all_config()
    assert all_config == config_manager.config
    
    all_config["test_key"] = "test_value"
    assert "test_key" not in config_manager.config


def test_reset_config(temp_dir):
    """测试重置配置"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    with tempfile.TemporaryDirectory() as temp_album_dir:
        config_manager.set_album_path(temp_album_dir)
        config_manager.update_setting("import_mode_default", "move")
        
        config_manager.reset_config()
        
        assert config_manager.config == config_manager._default_config()


def test_get_config_manager_singleton():
    """测试单例模式"""
    from backend.config_manager import get_config_manager
    
    config_manager1 = get_config_manager()
    config_manager2 = get_config_manager()
    
    assert config_manager1 is config_manager2


def test_get_album_path_obj(temp_dir):
    """测试获取相册路径对象"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    # 未设置相册路径时，应该返回None
    assert config_manager.get_album_path_obj() is None
    
    with tempfile.TemporaryDirectory() as temp_album_dir:
        config_manager.set_album_path(temp_album_dir)
        album_path_obj = config_manager.get_album_path_obj()
        assert album_path_obj is not None
        assert isinstance(album_path_obj, Path)
        assert str(album_path_obj.absolute()) == config_manager.get_album_path()


def test_set_album_path_only(temp_dir):
    """测试仅设置相册路径，不重建MD5索引"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    with tempfile.TemporaryDirectory() as temp_album_dir:
        result = config_manager.set_album_path_only(temp_album_dir)
        assert result
        
        expected_path = str(Path(temp_album_dir).absolute())
        assert config_manager.get_album_path() == expected_path


def test_set_album_path_invalid(temp_dir):
    """测试设置无效的相册路径"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    # 测试设置不存在的目录
    nonexistent_dir = str(Path(temp_dir) / "nonexistent")
    result = config_manager.set_album_path(nonexistent_dir)
    assert not result
    
    # 测试设置文件而非目录
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_file = f.name
    
    try:
        result = config_manager.set_album_path(temp_file)
        assert not result
    finally:
        import os
        os.unlink(temp_file)


def _make_photo_record(db, path: Path, **kwargs) -> Photo:
    """创建 Photo 记录并提交，返回对象。"""
    stat = path.stat()
    defaults = {
        "filename": path.name,
        "path": str(path),
        "size": stat.st_size,
        "md5_hash": f"md5_{path.name}",
        "created_at": datetime.now(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime),
        "media_date": datetime.fromtimestamp(stat.st_mtime),
        "file_type": "photo",
        "extension": path.suffix.lower(),
        "imported_at": datetime.now(),
    }
    defaults.update(kwargs)
    photo = Photo(**defaults)
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def _create_album_with_photos(db, name: str, photos: list, cover_photo: Photo = None) -> Album:
    """创建相册并关联照片，可选设置封面。"""
    album = Album(name=name)
    db.add(album)
    db.commit()
    db.refresh(album)
    for photo in photos:
        db.add(AlbumPhoto(album_id=album.id, photo_id=photo.id))
    if cover_photo:
        album.cover_photo_id = cover_photo.id
    db.commit()
    return album


def test_rebuild_preserves_favorites(temp_dir, in_memory_db):
    """重建索引后收藏状态保留。"""
    config_manager = create_config_manager_with_mock(temp_dir)
    db = in_memory_db()

    with tempfile.TemporaryDirectory() as album_dir:
        # 创建 3 个文件，其中 2 个标记为收藏
        files = []
        for i in range(3):
            fpath = Path(album_dir) / f"photo{i}.jpg"
            fpath.write_text(f"content {i}")
            files.append(fpath)

        _make_photo_record(db, files[0], is_favorite=True, favorited_at=datetime.now())
        _make_photo_record(db, files[1], is_favorite=False)
        _make_photo_record(db, files[2], is_favorite=True, favorited_at=datetime.now())

        with patch.object(config_manager, '_compute_md5', side_effect=lambda p: f"md5_{p.name}"):
            config_manager._rebuild_md5_index_for_album(Path(album_dir))

        db.expire_all()
        photos = {p.path: p for p in db.query(Photo).all()}
        assert len(photos) == 3
        assert photos[str(files[0])].is_favorite is True
        assert photos[str(files[1])].is_favorite is False
        assert photos[str(files[2])].is_favorite is True
        assert photos[str(files[0])].favorited_at is not None


def test_rebuild_preserves_album_associations(temp_dir, in_memory_db):
    """重建索引后相册关联和封面保留。"""
    config_manager = create_config_manager_with_mock(temp_dir)
    db = in_memory_db()

    with tempfile.TemporaryDirectory() as album_dir:
        files = []
        for i in range(3):
            fpath = Path(album_dir) / f"photo{i}.jpg"
            fpath.write_text(f"content {i}")
            files.append(fpath)

        p0 = _make_photo_record(db, files[0])
        p1 = _make_photo_record(db, files[1])
        p2 = _make_photo_record(db, files[2])

        album = _create_album_with_photos(db, "家庭", [p0, p1, p2], cover_photo=p1)
        original_ids = {str(files[i]): p.id for i, p in enumerate([p0, p1, p2])}

        with patch.object(config_manager, '_compute_md5', side_effect=lambda p: f"md5_{p.name}"):
            config_manager._rebuild_md5_index_for_album(Path(album_dir))

        db.expire_all()
        # photo_id 不变
        photos = {p.path: p for p in db.query(Photo).all()}
        for fpath, old_id in original_ids.items():
            assert photos[fpath].id == old_id

        # 相册关联不变
        album = db.query(Album).filter(Album.name == "家庭").first()
        linked_ids = {ap.photo_id for ap in db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album.id).all()}
        assert linked_ids == {photos[str(files[0])].id, photos[str(files[1])].id, photos[str(files[2])].id}
        assert album.cover_photo_id == photos[str(files[1])].id


def test_rebuild_preserves_title_description(temp_dir, in_memory_db):
    """重建索引后标题和描述保留。"""
    config_manager = create_config_manager_with_mock(temp_dir)
    db = in_memory_db()

    with tempfile.TemporaryDirectory() as album_dir:
        fpath = Path(album_dir) / "photo.jpg"
        fpath.write_text("content")
        _make_photo_record(db, fpath, title="旅行", description="夏天的海")

        with patch.object(config_manager, '_compute_md5', return_value="md5_photo.jpg"):
            config_manager._rebuild_md5_index_for_album(Path(album_dir))

        db.expire_all()
        photo = db.query(Photo).filter(Photo.path == str(fpath)).first()
        assert photo.title == "旅行"
        assert photo.description == "夏天的海"


def test_rebuild_handles_deleted_files(temp_dir, in_memory_db):
    """删除文件后重建索引，记录和相册关联被清理，相册本身保留。"""
    config_manager = create_config_manager_with_mock(temp_dir)
    db = in_memory_db()

    with tempfile.TemporaryDirectory() as album_dir:
        files = []
        for i in range(3):
            fpath = Path(album_dir) / f"photo{i}.jpg"
            fpath.write_text(f"content {i}")
            files.append(fpath)

        p0 = _make_photo_record(db, files[0])
        p1 = _make_photo_record(db, files[1])
        p2 = _make_photo_record(db, files[2])
        p1_id = p1.id
        album = _create_album_with_photos(db, "家庭", [p0, p1, p2], cover_photo=p1)

        # 删除 photo1 的物理文件
        files[1].unlink()

        with patch.object(config_manager, '_compute_md5', side_effect=lambda p: f"md5_{p.name}"):
            config_manager._rebuild_md5_index_for_album(Path(album_dir))

        db.expire_all()
        photos = {p.path: p for p in db.query(Photo).all()}
        assert len(photos) == 2
        assert str(files[1]) not in photos

        album = db.query(Album).filter(Album.name == "家庭").first()
        linked_ids = {ap.photo_id for ap in db.query(AlbumPhoto).filter(AlbumPhoto.album_id == album.id).all()}
        assert p1_id not in linked_ids
        assert album.cover_photo_id is None


def test_rebuild_handles_modified_files(temp_dir, in_memory_db):
    """文件被修改后重建索引，MD5 和 size 更新但收藏保留。"""
    config_manager = create_config_manager_with_mock(temp_dir)
    db = in_memory_db()

    with tempfile.TemporaryDirectory() as album_dir:
        fpath = Path(album_dir) / "photo.jpg"
        fpath.write_text("old content")
        photo = _make_photo_record(db, fpath, md5_hash="old_md5", is_favorite=True, favorited_at=datetime.now())
        old_id = photo.id

        # 修改文件内容，确保 mtime 变化
        time.sleep(0.1)
        fpath.write_text("new content longer")

        with patch.object(config_manager, '_compute_md5', return_value="new_md5"):
            config_manager._rebuild_md5_index_for_album(Path(album_dir))

        db.expire_all()
        photo = db.query(Photo).filter(Photo.path == str(fpath)).first()
        assert photo.id == old_id
        assert photo.md5_hash == "new_md5"
        assert photo.size == len("new content longer")
        assert photo.is_favorite is True
        assert photo.favorited_at is not None


def test_rebuild_migrates_path_on_album_rename(temp_dir, in_memory_db):
    """相册根目录改名后，path 前缀迁移且用户数据保留。"""
    config_manager = create_config_manager_with_mock(temp_dir)
    db = in_memory_db()

    with tempfile.TemporaryDirectory() as root:
        old_album_dir = Path(root) / "Photos"
        new_album_dir = Path(root) / "MyPhotos"
        old_album_dir.mkdir()
        new_album_dir.mkdir()

        old_sub = old_album_dir / "2024"
        old_sub.mkdir()
        # 文件只存在于新目录，但 DB 里有旧路径记录
        new_sub = new_album_dir / "2024"
        new_sub.mkdir()

        # 旧文件记录
        old_path = old_sub / "photo.jpg"
        old_path.write_text("content")
        photo = _make_photo_record(db, old_path, is_favorite=True, title="旧相册")

        # 把旧文件复制到新位置后删除旧文件（模拟改名）
        new_path = new_sub / "photo.jpg"
        shutil.copy2(old_path, new_path)
        old_path.unlink()

        # 设置 previous_album_path 模拟改名流程
        config_manager.config["previous_album_path"] = str(old_album_dir.absolute())

        with patch.object(config_manager, '_compute_md5', return_value="md5_photo.jpg"):
            config_manager._rebuild_md5_index_for_album(new_album_dir)

        db.expire_all()
        photos = db.query(Photo).all()
        assert len(photos) == 1
        assert photos[0].path == str(new_path)
        assert photos[0].id == photo.id
        assert photos[0].is_favorite is True
        assert photos[0].title == "旧相册"
        assert config_manager.config.get("previous_album_path") is None


def test_rebuild_without_previous_album_path(temp_dir, in_memory_db):
    """没有 previous_album_path（旧版本 DB 兼容）时正常增量更新。"""
    config_manager = create_config_manager_with_mock(temp_dir)
    db = in_memory_db()

    with tempfile.TemporaryDirectory() as album_dir:
        files = []
        for i in range(2):
            fpath = Path(album_dir) / f"photo{i}.jpg"
            fpath.write_text(f"content {i}")
            files.append(fpath)

        p0 = _make_photo_record(db, files[0], is_favorite=True, title="A")
        p1 = _make_photo_record(db, files[1], is_favorite=False, description="B")

        with patch.object(config_manager, '_compute_md5', side_effect=lambda p: f"md5_{p.name}"):
            config_manager._rebuild_md5_index_for_album(Path(album_dir))

        db.expire_all()
        photos = {p.path: p for p in db.query(Photo).all()}
        assert len(photos) == 2
        assert photos[str(files[0])].id == p0.id
        assert photos[str(files[0])].is_favorite is True
        assert photos[str(files[0])].title == "A"
        assert photos[str(files[1])].id == p1.id
        assert photos[str(files[1])].description == "B"


def test_get_album_path_invalid(temp_dir):
    """测试获取无效的相册路径"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    # 设置一个有效的相册路径
    with tempfile.TemporaryDirectory() as temp_album_dir:
        config_manager.set_album_path(temp_album_dir)
        
        # 验证路径有效
        assert config_manager.get_album_path() is not None
        
        # 模拟路径被删除
        import shutil
        shutil.rmtree(temp_album_dir)
        
        # 再次获取路径，应该返回None
        assert config_manager.get_album_path() is None


def test_nested_key_setting(temp_dir):
    """测试嵌套键设置"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    # 测试设置嵌套键（当前应该不支持）
    config_manager.update_setting("nested.key", "value")
    # 应该返回默认值
    assert config_manager.get_setting("nested.key", "default") == "default"


def test_get_setting_default(temp_dir):
    """测试获取不存在的设置时返回默认值"""
    config_manager = create_config_manager_with_mock(temp_dir)
    
    # 测试获取不存在的设置
    assert config_manager.get_setting("nonexistent_setting") is None
    assert config_manager.get_setting("nonexistent_setting", "default_value") == "default_value"
