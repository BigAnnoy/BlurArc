"""
配置管理模块
处理应用级别的配置文件和持久化存储
"""

import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 导入数据库模块（仅用于 MD5 索引重建）
from sqlalchemy import text
from .database import SessionLocal, Photo, Album, AlbumPhoto

# 共享常量和工具
from .constants import MEDIA_FORMATS, VIDEO_FORMATS
from .utils import compute_md5

logger = logging.getLogger(__name__)


def _get_user_data_dir() -> Path:
    """
    v0.7: 所有用户数据统一放在 ~/Documents/BlurArc/
    升级/卸载只动 exe 目录，用户数据不受影响
    """
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('USERPROFILE', Path.home()))
    else:  # macOS / Linux
        base = Path.home()
    
    data_dir = base / 'Documents' / 'BlurArc'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _get_app_data_dir() -> Path:
    """
    v0.7: 统一使用 ~/Documents/BlurArc/
    旧版本（v0.6）在 exe 旁边，已迁移
    """
    return _get_user_data_dir()


class ConfigManager:
    """
    配置管理器 - 负责 app 配置的读写
    
    配置文件路径：<app_data_dir>/.config/config.json
    包含内容：
    - album_path: 相册根目录
    - created_at: 首次创建时间
    - last_import: 最后一次导入时间
    - settings: 应用设置（导入模式等）
    """
    
    @property
    def CONFIG_DIR(self):
        """获取配置目录路径"""
        return _get_app_data_dir() / ".config"
    
    @property
    def CONFIG_FILE(self):
        """获取配置文件路径"""
        return self.CONFIG_DIR / "config.json"
    
    def __init__(self):
        """初始化配置管理器"""
        # 确保配置目录存在
        self._ensure_config_dir()
        
        # 加载配置到内存
        self.config = self._load_config()
    
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        如果不存在则返回默认配置
        """
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 配置文件读取失败: {e}，使用默认配置")
                return self._default_config()
        else:
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """返回默认配置"""
        return {
            "version": 2,
            "album_path": None,
            "created_at": None,
            "last_import": None,
            "settings": {
                "import_mode_default": "copy",  # copy 或 move
                "thumbnail_size": "200x200"     # 缩略图尺寸
            }
        }
    
    def _save_config(self):
        """保存配置到 JSON 文件"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.debug(f"配置已保存: {self.CONFIG_FILE}")
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            raise
    
    # ────────────────────────────────────────────
    # 公共 API
    # ────────────────────────────────────────────
    
    def is_first_run(self) -> bool:
        """
        检查是否首次运行
        首次运行 = album_path 为空
        """
        album_path = self.config.get("album_path")
        return album_path is None or album_path == ""
    
    def set_album_path(self, album_path: str) -> bool:
        """
        设置相册路径（同步版，含 MD5 索引重建）
        
        Args:
            album_path: 相册目录路径
            
        Returns:
            成功返回 True，失败返回 False
        """
        if not self.set_album_path_only(album_path):
            return False
        try:
            self._rebuild_md5_index_for_album(Path(album_path).absolute())
            return True
        except Exception as e:
            logger.error(f"重建 MD5 索引失败: {e}")
            return False

    def set_album_path_only(self, album_path: str) -> bool:
        """
        仅写入相册路径配置，不触发 MD5 索引重建。
        供异步重建场景使用（api_server 先调此方法，再在后台线程调 _rebuild_md5_index_for_album）。
        
        Args:
            album_path: 相册目录路径
            
        Returns:
            成功返回 True，失败返回 False
        """
        album_path_obj = Path(album_path)
        
        # 验证路径
        if not album_path_obj.exists():
            logger.error(f"❌ 路径不存在: {album_path}")
            return False
        
        if not album_path_obj.is_dir():
            logger.error(f"❌ 不是目录: {album_path}")
            return False
        
        album_path_abs = str(album_path_obj.absolute())
        
        # 把旧 album_path 挪到 previous_album_path，用于后续 path 迁移
        old_album_path = self.config.get("album_path")
        if old_album_path and old_album_path != album_path_abs:
            self.config["previous_album_path"] = old_album_path
        
        # 更新内存配置
        self.config["album_path"] = album_path_abs
        self.config["created_at"] = datetime.now().isoformat()
        
        try:
            # 保存到 JSON 文件
            self._save_config()
            return True
        except Exception as e:
            logger.error(f"写入相册路径失败: {e}")
            return False


    def _compute_md5(self, file_path: Path) -> Optional[str]:
        """计算文件MD5（委托给 utils.compute_md5）"""
        return compute_md5(file_path)

    def _rebuild_md5_index_for_album(self, album_path: Path, progress_cb=None) -> None:
        """
        重建当前相册目录的索引（增量更新，保留用户数据）。

        流程：
        1) path 迁移（若相册根目录变了，把旧前缀替换成新前缀）
        2) 查询现有所有 Photo
        3) 扫描新目录媒体文件
        4) 三分支比对：
           - UPDATE：path 仍存在，按指纹判断是否重算 MD5
           - INSERT：path 是新的
           - DELETE：path 在 DB 有但磁盘没有，清掉记录 + 相册关联
        5) 保留 is_favorite / favorited_at / title / description / id

        Args:
            album_path: 相册根目录
            progress_cb: 可选回调 (message: str, percent: int)
        """
        def _cb(msg, pct):
            if progress_cb:
                try:
                    progress_cb(msg, pct)
                except Exception:
                    pass

        def _escape_like(s: str) -> str:
            """转义 LIKE 通配符 \\ % _"""
            return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        media_formats = MEDIA_FORMATS
        video_formats = VIDEO_FORMATS

        db = SessionLocal()
        try:
            # ============================================================
            # Phase 1: path 迁移
            # ============================================================
            prev_album_path = self.config.get("previous_album_path")
            new_album_path_abs = str(album_path.absolute()).rstrip("\\/")

            if prev_album_path:
                prev_abs = prev_album_path.rstrip("\\/")
                if prev_abs.lower() != new_album_path_abs.lower():
                    _cb('检测到相册路径变化，迁移 path 前缀...', 3)
                    # 严格匹配：必须以"旧前缀 + 路径分隔符"开头
                    # 避免 D:\Photos 误匹配 D:\PhotosBackup
                    old_prefix_with_sep = prev_abs.rstrip("\\/") + os.sep
                    new_prefix_with_sep = new_album_path_abs.rstrip("\\/") + os.sep

                    # LIKE pattern 必须用旧前缀（不含末尾分隔符）拼接 "\\%"，
                    # 其中 "\\" 表示字面 "\"，"%" 是通配符。
                    # 如果写成 "\\%"（仅一个反斜杠），SQLite 会把它解析为字面 "%"，
                    # 导致匹配失败；如果写成旧写法 "_escape_like(old_prefix_with_sep) + '%'"，
                    # 末尾的 "\\%" 又会被解析为字面 "%"，从而误匹配 PhotosBackup。
                    old_prefix_like = _escape_like(prev_abs) + "\\\\%"

                    db.execute(
                        text(
                            "UPDATE photos "
                            "SET path = :new_prefix || SUBSTR(path, LENGTH(:old_prefix) + 1) "
                            "WHERE path LIKE :old_prefix_like ESCAPE '\\'"
                        ),
                        {
                            "new_prefix": new_prefix_with_sep,
                            "old_prefix": old_prefix_with_sep,
                            "old_prefix_like": old_prefix_like,
                        }
                    )
                    db.commit()
                    migrated = db.query(Photo).filter(Photo.path.like(new_prefix_with_sep + "%", escape="\\")).count()
                    logger.info(f"[rebuild] path 迁移完成：{prev_abs} → {new_album_path_abs}，影响 {migrated} 条记录")

                # 清除 previous_album_path（迁移完成或路径没变）
                self.config["previous_album_path"] = None
                self._save_config()

            # ============================================================
            # Phase 2: 查询现有所有 Photo
            # ============================================================
            _cb('正在查询现有索引...', 5)
            existing_photos = db.query(Photo).all()
            existing_map = {p.path: p for p in existing_photos}

            # ============================================================
            # Phase 3: 扫描新目录
            # ============================================================
            _cb('正在扫描文件列表...', 10)
            all_files = [
                f for f in album_path.rglob('*')
                if f.is_file() and f.suffix.lower() in media_formats
            ]
            total = len(all_files)
            new_paths_set = {str(f) for f in all_files}
            now = datetime.now()

            # ============================================================
            # Phase 4: 比对 + UPDATE + INSERT
            # ============================================================
            new_photos_to_add = []
            for idx, file in enumerate(all_files, 1):
                pct = 10 + int(idx / total * 70) if total else 80
                _cb(f'正在比对 ({idx}/{total})...', pct)

                file_path_str = str(file)
                try:
                    stat = file.stat()
                except Exception:
                    continue

                ext = file.suffix.lower()
                file_mtime = stat.st_mtime

                existing = existing_map.get(file_path_str)
                if existing:
                    # path 已存在 → 看指纹决定是否重算 MD5
                    existing_mtime = existing.modified_at.timestamp() if existing.modified_at else None
                    if existing.size == stat.st_size and existing_mtime == file_mtime:
                        # 指纹完全一致 → 跳过
                        continue
                    # 指纹变了 → 重算 MD5
                    existing.md5_hash = self._compute_md5(file)
                    existing.size = stat.st_size
                    existing.modified_at = datetime.fromtimestamp(file_mtime)
                    existing.media_date = datetime.fromtimestamp(file_mtime)
                    # 不动 is_favorite / favorited_at / title / description / id
                else:
                    # 新文件 → 创建新 Photo
                    new_photos_to_add.append(Photo(
                        filename=file.name,
                        path=file_path_str,
                        size=stat.st_size,
                        md5_hash=self._compute_md5(file),
                        created_at=now,
                        modified_at=datetime.fromtimestamp(file_mtime),
                        media_date=datetime.fromtimestamp(file_mtime),
                        file_type='video' if ext in video_formats else 'photo',
                        extension=ext,
                        imported_at=now,
                    ))

            # ============================================================
            # Phase 5: DELETE 分支（清理已不存在文件 + 相册关联）
            # ============================================================
            _cb('正在清理已删除文件...', 85)
            to_delete_ids = [p.id for p in existing_photos if p.path not in new_paths_set]
            if to_delete_ids:
                # Step 1: 清掉 album_photos 关联
                db.query(AlbumPhoto).filter(AlbumPhoto.photo_id.in_(to_delete_ids)).delete(synchronize_session=False)
                # Step 2: albums.cover_photo_id 置 NULL（保留相册本身）
                db.query(Album).filter(Album.cover_photo_id.in_(to_delete_ids)).update(
                    {Album.cover_photo_id: None}, synchronize_session=False
                )
                # Step 3: 删 photos 记录
                db.query(Photo).filter(Photo.id.in_(to_delete_ids)).delete(synchronize_session=False)

            # ============================================================
            # Phase 6: INSERT 新文件
            # ============================================================
            _cb('正在写入新文件...', 90)
            if new_photos_to_add:
                db.add_all(new_photos_to_add)

            db.commit()
            _cb('索引重建完成', 100)
            logger.info(
                f"✓ 重建索引完成: {album_path}，"
                f"共 {total} 个文件，"
                f"新增 {len(new_photos_to_add)} 个，"
                f"删除 {len(to_delete_ids)} 个"
            )
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_album_path(self) -> Optional[str]:
        """获取相册路径"""
        album_path = self.config.get("album_path")
        
        # 验证路径是否仍然存在
        if album_path:
            album_path_obj = Path(album_path)
            if not album_path_obj.exists() or not album_path_obj.is_dir():
                logger.warning(f"⚠️ 相册路径不存在或不是目录: {album_path}")
                # 把旧值挪到 previous_album_path，用于后续 path 迁移
                self.config["previous_album_path"] = album_path
                self.config["album_path"] = None
                self._save_config()
                return None
        return album_path
    
    def get_album_path_obj(self) -> Optional[Path]:
        """获取相册路径对象"""
        album_path = self.get_album_path()
        return Path(album_path) if album_path else None
    
    def set_last_import(self, timestamp: Optional[str] = None):
        """
        更新最后导入时间
        
        Args:
            timestamp: ISO 格式时间戳，默认为当前时间
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 更新内存配置
        self.config["last_import"] = timestamp
        
        try:
            # 保存到 JSON 文件
            self._save_config()
        except Exception as e:
            logger.error(f"设置最后导入时间失败: {e}")
    
    def get_last_import(self) -> Optional[str]:
        """获取最后导入时间"""
        return self.config.get("last_import")
    
    def update_setting(self, key: str, value: Any):
        """
        更新应用设置
        
        Args:
            key: 设置项 key（嵌套用 "." 分隔，如 "import_mode_default"）
            value: 设置值
        """
        # 对于简单的一级 key
        if "." not in key:
            if "settings" not in self.config:
                self.config["settings"] = {}
            self.config["settings"][key] = value
            
            try:
                # 保存到 JSON 文件
                self._save_config()
            except Exception as e:
                logger.error(f"更新设置失败: {e}")
        else:
            # 对于嵌套 key（暂时不支持，可扩展）
            pass
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取应用设置
        
        Args:
            key: 设置项 key
            default: 默认值
            
        Returns:
            设置值，不存在则返回 default
        """
        if "." not in key:
            settings = self.config.get("settings", {})
            return settings.get(key, default)
        return default
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置（用于调试）"""
        return self.config.copy()
    
    def reset_config(self):
        """重置配置为默认值（仅用于测试）"""
        # 重置内存配置
        self.config = self._default_config()
        
        try:
            # 保存到 JSON 文件
            self._save_config()
        except Exception as e:
            logger.error(f"重置配置失败: {e}")


# ────────────────────────────────────────────
# 单例实例（全局使用）
# ────────────────────────────────────────────
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


# ────────────────────────────────────────────
# 测试代码
# ────────────────────────────────────────────
if __name__ == "__main__":
    # 测试配置管理器
    config = ConfigManager()
    
    print("\n=== ConfigManager 测试 ===\n")
    
    print(f"首次运行: {config.is_first_run()}")
    print(f"相册路径: {config.get_album_path()}")
    print(f"配置: {json.dumps(config.get_all_config(), indent=2, ensure_ascii=False)}")
    
    # 测试设置相册路径
    test_path = Path.home() / "Pictures" / "TestAlbum"
    test_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n设置相册路径: {test_path}")
    if config.set_album_path(str(test_path)):
        print("✓ 设置成功")
        print(f"相册路径: {config.get_album_path()}")
        print(f"首次运行: {config.is_first_run()}")
    
    print(f"\n最后导入时间: {config.get_last_import()}")
    config.set_last_import()
    print(f"更新后: {config.get_last_import()}")
    
    print(f"\n最终配置: {json.dumps(config.get_all_config(), indent=2, ensure_ascii=False)}")
