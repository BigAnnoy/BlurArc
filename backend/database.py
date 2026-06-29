"""
数据库模块
使用SQLite和SQLAlchemy实现数据持久化
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Index, create_engine, text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func

# v0.7: 数据目录统一迁移到 ~/Documents/BlurArc/
# 延迟导入避免循环依赖
def _get_db_path():
    """获取数据库路径"""
    try:
        from .config_manager import _get_user_data_dir
        return _get_user_data_dir() / ".config" / "photo_manager.db"
    except ImportError:
        # 回退：直接计算
        import os
        if os.name == 'nt':
            base = Path(os.environ.get('USERPROFILE', Path.home()))
        else:
            base = Path.home()
        return base / 'Documents' / 'BlurArc' / '.config' / 'photo_manager.db'

# 数据库文件路径
DB_PATH = _get_db_path()

# 创建数据库目录
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# 创建数据库引擎
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


class Photo(Base):
    """照片和视频表"""
    __tablename__ = "photos"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    path = Column(Text, nullable=False, unique=True)
    size = Column(Integer, nullable=False)
    md5_hash = Column(String(32), index=True)  # 不加 unique：同一 MD5 允许多个 _dup 副本
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(DateTime(timezone=True), onupdate=func.now())
    # media_date 加索引：手机端 /api/mobile/photos/sections 按月 GROUP BY 必须扫 media_date，
    # 没索引时 20k+ 照片首查会扫整表（这就是手机首次"加载中"卡住的根因之一）。
    media_date = Column(DateTime(timezone=True), index=True)
    file_type = Column(String(10), nullable=False)  # 'photo' or 'video'
    extension = Column(String(10), nullable=False)
    thumbnail_path = Column(Text)
    imported_at = Column(DateTime(timezone=True), server_default=func.now())
    is_favorite = Column(Boolean, default=False, index=True)
    favorited_at = Column(DateTime(timezone=True))  # v0.7 新增：收藏时间
    title = Column(String(255))  # v0.7 新增：标题（XMP dc:title）
    description = Column(Text)  # v0.7 新增：描述（XMP dc:description）
    
    # 关联关系
    tags = relationship("Tag", secondary="photo_tags", back_populates="photos")
    albums = relationship("Album", secondary="album_photos", back_populates="photos")


class Tag(Base):
    """标签表（预留功能，暂未启用）"""
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联关系
    photos = relationship("Photo", secondary="photo_tags", back_populates="tags")


class PhotoTag(Base):
    """照片和标签关联表（预留功能，暂未启用）"""
    __tablename__ = "photo_tags"
    
    photo_id = Column(Integer, ForeignKey("photos.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Album(Base):
    """相册表（v0.7 启用）"""
    __tablename__ = "albums"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text)
    cover_photo_id = Column(Integer, ForeignKey('photos.id'), nullable=True)  # v0.7 新增：封面照片
    
    # 关联关系
    photos = relationship("Photo", secondary="album_photos", back_populates="albums")
    cover_photo = relationship("Photo", foreign_keys=[cover_photo_id])


class AlbumPhoto(Base):
    """相册和照片关联表（预留功能，暂未启用）"""
    __tablename__ = "album_photos"
    
    album_id = Column(Integer, ForeignKey("albums.id"), primary_key=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), primary_key=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())


class ImportHistory(Base):
    """导入历史表"""
    __tablename__ = "import_history"
    
    id = Column(Integer, primary_key=True, index=True)
    source_path = Column(Text, nullable=False)
    target_path = Column(Text, nullable=False)
    total_files = Column(Integer, nullable=False)
    imported_files = Column(Integer, nullable=False)
    skipped_files = Column(Integer, nullable=False)
    failed_files = Column(Integer, nullable=False)
    total_size = Column(Integer, nullable=True)  # 总字节数（可为空以兼容旧数据）
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False)  # pending/processing/completed/failed/cancelled


class Setting(Base):
    """设置表"""
    __tablename__ = "settings"
    
    id: int = Column(Integer, primary_key=True, index=True)
    key: str = Column(String(50), nullable=False, unique=True)
    value: str = Column(Text, nullable=False)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: datetime = Column(DateTime(timezone=True), onupdate=func.now())


def init_db():
    """初始化数据库"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 迁移：为 photos.media_date 加索引（首次移动端首查卡住的根因）
    # create_all 不会给旧表补索引，必须手动建。幂等：IF NOT EXISTS
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_photos_media_date ON photos (media_date)"
                )
            )
            conn.commit()
    except Exception:
        pass  # 表尚未创建时忽略（由 create_all 负责）

    # 迁移：Plan B - 优化 3 前置
    # 为 photos.path 创建命名 UNIQUE 索引，支持 _import_file 的 INSERT OR IGNORE 优化
    # 幂等：IF NOT EXISTS；Photo 模型 unique=True 也会创建隐式索引，但此处显式命名便于引用
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_photo_path_unique ON photos (path)"
                )
            )
            conn.commit()
    except Exception:
        pass  # 表尚未创建时忽略（由 create_all 负责）

    # 迁移：为旧数据库补加 total_size 列（幂等，仅当列不存在时执行）
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("PRAGMA table_info(import_history)")
            )
            columns = [row[1] for row in result]
            if 'total_size' not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE import_history ADD COLUMN total_size INTEGER"
                    )
                )
                conn.commit()
    except Exception:
        pass  # 表尚未创建时忽略（由 create_all 负责）
    
    # 迁移：移除 photos 表的 md5_hash 唯一约束（如果存在）
    # SQLite 不支持直接删除约束，需要重建表
    try:
        with engine.connect() as conn:
            # 检查是否存在唯一索引
            result = conn.execute(
                text("PRAGMA index_list(photos)")
            )
            indexes = [row for row in result]
            unique_md5_index = None
            for idx in indexes:
                # idx: (seq, name, unique, origin, partial)
                if idx[2] == 1 and 'md5' in idx[1].lower():  # unique=1 且名称包含 md5
                    unique_md5_index = idx[1]
                    break
            
            if unique_md5_index:
                # 删除唯一索引（SQLite 支持删除索引）
                conn.execute(
                    text(f"DROP INDEX IF EXISTS {unique_md5_index}")
                )
                conn.commit()
                print(f"已移除 photos 表的 MD5 唯一约束: {unique_md5_index}")
    except Exception as e:
        print(f"移除 MD5 唯一约束时出错（可能已不存在）: {e}")
        pass
    
    # v0.7 迁移：为 photos 表添加新字段
    try:
        with engine.connect() as conn:
            # 检查 photos 表现有列
            result = conn.execute(text("PRAGMA table_info(photos)"))
            photo_columns = [row[1] for row in result]

            # 添加 favorited_at 字段
            if 'favorited_at' not in photo_columns:
                conn.execute(text("ALTER TABLE photos ADD COLUMN favorited_at DATETIME"))
                conn.commit()
                print("已添加 photos.favorited_at 字段")

            # 添加 title 字段
            if 'title' not in photo_columns:
                conn.execute(text("ALTER TABLE photos ADD COLUMN title VARCHAR(255)"))
                conn.commit()
                print("已添加 photos.title 字段")

            # 添加 description 字段
            if 'description' not in photo_columns:
                conn.execute(text("ALTER TABLE photos ADD COLUMN description TEXT"))
                conn.commit()
                print("已添加 photos.description 字段")

            # 检查 albums 表现有列
            result = conn.execute(text("PRAGMA table_info(albums)"))
            album_columns = [row[1] for row in result]

            # 添加 cover_photo_id 字段
            if 'cover_photo_id' not in album_columns:
                conn.execute(text("ALTER TABLE albums ADD COLUMN cover_photo_id INTEGER"))
                conn.commit()
                print("已添加 albums.cover_photo_id 字段")

            # 检查 album_photos 表现有列
            result = conn.execute(text("PRAGMA table_info(album_photos)"))
            album_photo_columns = [row[1] for row in result]

            # 添加 added_at 字段
            if 'added_at' not in album_photo_columns:
                conn.execute(text("ALTER TABLE album_photos ADD COLUMN added_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                conn.commit()
                print("已添加 album_photos.added_at 字段")

            # 添加 sort_order 字段（先建字段，拖动重排后续实现）
            if 'sort_order' not in album_photo_columns:
                conn.execute(text("ALTER TABLE album_photos ADD COLUMN sort_order INTEGER DEFAULT 0"))
                conn.commit()
                print("已添加 album_photos.sort_order 字段")
    except Exception as e:
        print(f"v0.7 字段迁移时出错: {e}")
        pass

    # v0.7 迁移：为 photos.favorited_at 创建索引
    # 收藏列表 GET /api/photos/favorites 默认按 favorited_at desc 排序，
    # 没索引时全表扫描。create_all 不会给旧表补索引，必须手动建。幂等：IF NOT EXISTS。
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_photos_favorited_at ON photos (favorited_at)"
                )
            )
            conn.commit()
    except Exception:
        pass  # 表尚未创建时忽略（由 create_all 负责）

    # 初始化默认设置
    db = SessionLocal()
    try:
        # 检查是否已存在设置
        if db.query(Setting).count() == 0:
            # 添加默认设置
            default_settings = [
                Setting(key="import_mode_default", value="copy"),
                Setting(key="thumbnail_size", value="200x200"),
                Setting(key="cache_duration", value="3600"),  # 缓存时长（秒）
                Setting(key="dark_mode", value="false"),
            ]
            db.add_all(default_settings)
            db.commit()
    finally:
        db.close()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_setting(key: str, default: str | None = None) -> str | None:
    """获取设置值"""
    db = SessionLocal()
    try:
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            # 确保返回字符串类型
            value = setting.value
            return str(value) if value is not None else default
        return default
    finally:
        db.close()


def set_setting(key: str, value: str) -> bool:
    """设置设置值"""
    db = SessionLocal()
    try:
        setting = db.query(Setting).filter(Setting.key == key).first()
        # 确保value是字符串类型
        str_value = str(value)
        if setting:
            # 直接赋值，SQLAlchemy会处理类型转换
            setting.value = str_value
        else:
            # 创建新对象时直接传递字符串值
            setting = Setting(key=key, value=str_value)
            db.add(setting)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        return False
    finally:
        db.close()


# 初始化数据库
if __name__ == "__main__":
    init_db()
    print(f"数据库已初始化: {DB_PATH}")
