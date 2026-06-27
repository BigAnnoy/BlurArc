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
from .database import SessionLocal, Photo

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
        重建当前相册目录的MD5索引：
        1) 清空 photos 表（旧目录记录）
        2) 扫描新目录媒体文件
        3) 重建新目录的 path/md5 记录
        
        Args:
            album_path: 相册根目录
            progress_cb: 可选回调 (message: str, percent: int)，用于上报进度
        """
        def _cb(msg, pct):
            if progress_cb:
                try:
                    progress_cb(msg, pct)
                except Exception:
                    pass

        media_formats = MEDIA_FORMATS
        video_formats = VIDEO_FORMATS


        db = SessionLocal()
        try:
            _cb('正在清空旧索引...', 5)
            # 清空旧相册记录（包含旧MD5）
            db.query(Photo).delete()
            db.commit()

            # 先收集文件列表，以便计算进度
            _cb('正在扫描文件列表...', 10)
            all_files = [
                f for f in album_path.rglob('*')
                if f.is_file() and f.suffix.lower() in media_formats
            ]
            total = len(all_files)

            now = datetime.now()

            for idx, file in enumerate(all_files, 1):
                pct = 10 + int(idx / total * 85) if total else 95
                _cb(f'正在建立索引 ({idx}/{total})...', pct)

                try:
                    stat = file.stat()
                except Exception:
                    continue

                ext = file.suffix.lower()
                # md5_hash 不再有 unique 约束，直接保存所有文件的真实 MD5
                # 保留重复 MD5 记录，确保去重检测能正常工作
                md5_hash = self._compute_md5(file)

                photo = Photo(
                    filename=file.name,
                    path=str(file),
                    size=stat.st_size,
                    md5_hash=md5_hash,
                    created_at=now,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    media_date=datetime.fromtimestamp(stat.st_mtime),
                    file_type='video' if ext in video_formats else 'photo',
                    extension=ext,
                    imported_at=now,
                )
                db.add(photo)

            db.commit()
            _cb('索引重建完成', 100)
            logger.info(f"✓ 已重建相册MD5索引: {album_path}，共 {total} 个文件")
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
                # 重置相册路径为 None
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
