"""
缩略图管理模块 - 处理照片和视频的缩略图生成与缓存
支持异步生成、统一接口、缓存策略
"""

import os
import io
import hashlib
import logging
import threading
import concurrent.futures
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from PIL import Image, UnidentifiedImageError

# 尝试加载 pillow-heif（HEIC 支持）
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    _HEIF_AVAILABLE = True
except ImportError:
    _HEIF_AVAILABLE = False

# 数据库模块
from .database import SessionLocal, Photo

# 视频处理模块
from .video_processor import VideoProcessor

logger = logging.getLogger(__name__)


class ThumbnailManager:
    """缩略图管理器"""
    
    def __init__(self):
        self.cache_dir = Path('~/.photomanager/thumbnails').expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取缩略图配置
        self.thumbnail_size = self._get_thumbnail_size()
        
        # 创建线程池
        cpu_count = os.cpu_count() or 2
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, cpu_count - 1)
        )
        
        # 图片文件扩展名
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.ico', '.heic'}
        
        # 视频文件扩展名
        self.video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp'}
    
    def _get_thumbnail_size(self) -> Tuple[int, int]:
        """获取缩略图尺寸配置"""
        try:
            from .config_manager import get_config_manager
            config = get_config_manager()
            size_str = config.get_setting("thumbnail_size", "200x200")
            if 'x' in size_str:
                width, height = map(int, size_str.split('x'))
                return (width, height)
        except Exception as e:
            logger.warning(f"获取缩略图尺寸配置失败: {e}")
        
        # 默认尺寸
        return (200, 200)
    
    def _generate_cache_key(self, file_path: Path) -> str:
        """生成缓存键"""
        file_stat = file_path.stat()
        file_info = f"{str(file_path)}:{file_stat.st_mtime}:{file_stat.st_size}"
        return hashlib.md5(file_info.encode()).hexdigest()
    
    def get_thumbnail(self, file_path: str) -> Optional[Path]:
        """
        获取文件的缩略图路径
        如果缓存不存在，会异步生成
        
        Args:
            file_path: 文件路径
            
        Returns:
            缩略图路径，如果生成失败返回None
        """
        file_path = Path(file_path)
        
        if not file_path.exists() or not file_path.is_file():
            return None
        
        # 生成缓存文件路径
        cache_key = self._generate_cache_key(file_path)
        cache_file = self.cache_dir / f"{cache_key}.jpg"
        
        # 检查缓存是否存在
        if cache_file.exists():
            logger.debug(f"使用缓存的缩略图: {cache_file}")
            return cache_file
        
        # 异步生成缩略图
        self.executor.submit(self._generate_thumbnail_sync, file_path, cache_file)
        
        # 返回None，调用方可以在之后重试
        return None
    
    def get_thumbnail_sync(self, file_path: str) -> Optional[Path]:
        """
        同步获取文件的缩略图路径
        如果缓存不存在，会立即生成
        
        Args:
            file_path: 文件路径
            
        Returns:
            缩略图路径，如果生成失败返回None
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return None
        
        if not file_path.is_file():
            logger.warning(f"不是文件: {file_path}")
            return None
        
        # 生成缓存文件路径
        cache_key = self._generate_cache_key(file_path)
        cache_file = self.cache_dir / f"{cache_key}.jpg"
        
        # 检查缓存是否存在
        if cache_file.exists():
            logger.debug(f"使用缓存的缩略图: {cache_file}")
            return cache_file
        
        # 同步生成缩略图
        logger.info(f"生成缩略图: {file_path}")
        return self._generate_thumbnail_sync(file_path, cache_file)
    
    def _generate_thumbnail_sync(self, file_path: Path, cache_file: Path) -> Optional[Path]:
        """
        同步生成缩略图
        
        Args:
            file_path: 原始文件路径
            cache_file: 缓存文件路径
            
        Returns:
            缩略图路径，如果生成失败返回None
        """
        logger.debug(f"生成新的缩略图: {file_path} -> {cache_file}")
        
        try:
            # 根据文件类型生成缩略图
            suffix = file_path.suffix.lower()
            
            if suffix in self.image_extensions:
                # 图片文件
                return self._generate_image_thumbnail(file_path, cache_file)
            elif suffix in self.video_extensions:
                # 视频文件
                return self._generate_video_thumbnail(file_path, cache_file)
            else:
                logger.warning(f"不支持的文件类型: {file_path}")
                return None
        
        except Exception as e:
            logger.error(f"生成缩略图失败 {file_path}: {e}")
            return None
    
    def _generate_image_thumbnail(self, image_path: Path, output_path: Path) -> Optional[Path]:
        """
        生成图片缩略图
        
        Args:
            image_path: 原始图片路径
            output_path: 缩略图输出路径
            
        Returns:
            缩略图路径，如果生成失败返回None
        """
        try:
            # 打开原始图片
            img = Image.open(str(image_path))
            
            # 转换为 RGB 模式（处理透明通道）
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode == 'P' and 'transparency' in img.info:
                # 调色板模式需先转 RGBA 才能取到 alpha 通道
                rgba = img.convert('RGBA')
                background = Image.new('RGB', rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 生成缩略图（保持比例）
            img.thumbnail(self.thumbnail_size, Image.LANCZOS)
            
            # 保存到缓存目录
            img.save(str(output_path), 'JPEG', quality=85, optimize=True, progressive=True)
            
            # 更新数据库中的缩略图路径
            self._update_photo_thumbnail_path(image_path, output_path)
            
            return output_path
            
        except UnidentifiedImageError:
            logger.error(f"无法识别的图片格式: {image_path}")
            return None
        except Exception as e:
            logger.error(f"生成图片缩略图失败 {image_path}: {e}")
            return None
    
    def _generate_video_thumbnail(self, video_path: Path, output_path: Path) -> Optional[Path]:
        """
        生成视频缩略图
        
        Args:
            video_path: 原始视频路径
            output_path: 缩略图输出路径
            
        Returns:
            缩略图路径，如果生成失败返回None
        """
        try:
            # 使用视频处理器生成缩略图
            success = VideoProcessor.generate_thumbnail(
                str(video_path), 
                str(output_path)
            )
            
            if success:
                # 更新数据库中的缩略图路径
                self._update_photo_thumbnail_path(video_path, output_path)
                return output_path
            else:
                logger.error(f"生成视频缩略图失败: {video_path}")
                return None
                
        except Exception as e:
            logger.error(f"生成视频缩略图失败 {video_path}: {e}")
            return None
    
    def _update_photo_thumbnail_path(self, file_path: Path, thumbnail_path: Path) -> None:
        """
        更新数据库中的缩略图路径
        
        Args:
            file_path: 原始文件路径
            thumbnail_path: 缩略图路径
        """
        db = SessionLocal()
        try:
            photo = db.query(Photo).filter(Photo.path == str(file_path)).first()
            if photo:
                photo.thumbnail_path = str(thumbnail_path)
                photo.modified_at = datetime.now()
                db.commit()
        except Exception as e:
            logger.warning(f"更新数据库缩略图路径失败: {e}")
            db.rollback()
        finally:
            db.close()
    
    # -------------------------------------------------------------------------
    # HEIC / 特殊格式预览支持
    # -------------------------------------------------------------------------

    # 浏览器原生支持的格式 — 直接返回原文件，无需转换
    BROWSER_NATIVE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    # 需要服务端转 JPEG 后才能在浏览器中预览的格式
    CONVERT_EXTS = {'.heic', '.heif', '.tiff', '.tif', '.bmp', '.ico'}

    def get_preview_jpeg(self, file_path: str) -> Optional[Path]:
        """
        返回适合浏览器预览的文件路径。
        - 原生格式（jpg/png/gif/webp）→ 直接返回原始路径
        - HEIC/TIFF/BMP/ICO → 转换为 JPEG 并写入缓存目录后返回缓存路径
        - 其他格式（视频等）→ 返回 None，由调用方处理
        
        Args:
            file_path: 原始文件路径
        Returns:
            可直接被浏览器渲染的文件路径，失败返回 None
        """
        file_path = Path(file_path)
        if not file_path.exists() or not file_path.is_file():
            return None

        ext = file_path.suffix.lower()

        # 浏览器原生支持 → 直接返回原始文件
        if ext in self.BROWSER_NATIVE_EXTS:
            return file_path

        # 需要转换的格式
        if ext in self.CONVERT_EXTS:
            # 以 (路径 + 修改时间 + 大小 + ":preview") 生成缓存键
            try:
                st = file_path.stat()
                key_str = f"{file_path}:{st.st_mtime}:{st.st_size}:preview"
            except OSError:
                key_str = f"{file_path}:preview"

            import hashlib as _hashlib
            cache_key = _hashlib.md5(key_str.encode()).hexdigest()
            cache_file = self.cache_dir / f"{cache_key}_preview.jpg"

            if cache_file.exists():
                return cache_file

            # 执行转换
            logger.info(f"转换 {ext} 预览图: {file_path} -> {cache_file}")
            try:
                img = Image.open(str(file_path))
                # 处理透明通道
                if img.mode in ('RGBA', 'LA'):
                    # 直接取 alpha 通道作为 mask
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[-1])
                    img = bg
                elif img.mode == 'P' and 'transparency' in img.info:
                    # 调色板模式需先转 RGBA，再合并白底
                    rgba = img.convert('RGBA')
                    bg = Image.new('RGB', rgba.size, (255, 255, 255))
                    bg.paste(rgba, mask=rgba.split()[-1])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(str(cache_file), 'JPEG', quality=92, optimize=True)
                logger.info(f"预览图转换完成: {cache_file}")
                return cache_file
            except Exception as e:
                logger.error(f"预览图转换失败 {file_path}: {e}")
                return None

        # 其他格式（视频等）→ 不处理
        return None

    def generate_thumbnails_batch(self, file_paths: List[str]) -> None:
        """
        批量生成缩略图
        
        Args:
            file_paths: 文件路径列表
        """
        for file_path in file_paths:
            self.executor.submit(self.get_thumbnail_sync, file_path)
    
    def cleanup_cache(self, max_age_days: int = 30) -> None:
        """
        清理过期的缓存文件
        
        Args:
            max_age_days: 缓存最大保留天数
        """
        current_time = datetime.now()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        logger.info(f"开始清理缩略图缓存，保留最近 {max_age_days} 天的缓存")
        
        try:
            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file() and cache_file.suffix == '.jpg':
                    try:
                        file_stat = cache_file.stat()
                        file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                        if (current_time - file_mtime).total_seconds() > max_age_seconds:
                            cache_file.unlink()
                            logger.debug(f"已清理过期缓存: {cache_file}")
                    except Exception as e:
                        logger.debug(f"清理缓存文件失败 {cache_file}: {e}")
            
            logger.info("缩略图缓存清理完成")
        
        except Exception as e:
            logger.error(f"清理缩略图缓存失败: {e}")

    def cleanup_cache_by_size(self, max_size_mb: float = 500) -> dict:
        """
        按缓存总大小限制清理缓存文件（LRU 策略）。

        超过 max_size_mb 时，按最后访问时间（atime）从旧到新删除，
        直到总大小低于阈值。

        Args:
            max_size_mb: 允许的最大缓存大小（MB），默认 500 MB

        Returns:
            dict: {deleted_count, freed_mb, remaining_mb}
        """
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        deleted_count = 0
        freed_bytes = 0

        try:
            # 收集所有缓存文件及其信息
            cache_files = []
            total_bytes = 0
            for f in self.cache_dir.iterdir():
                if f.is_file() and f.suffix in ('.jpg', '.jpeg', '.png', '.webp'):
                    try:
                        st = f.stat()
                        cache_files.append((st.st_atime, st.st_size, f))
                        total_bytes += st.st_size
                    except Exception:
                        pass

            if total_bytes <= max_size_bytes:
                return {
                    'deleted_count': 0,
                    'freed_mb': 0.0,
                    'remaining_mb': round(total_bytes / (1024 * 1024), 2),
                }

            # 按访问时间升序（最旧的排前面）
            cache_files.sort(key=lambda x: x[0])

            for atime, size, f in cache_files:
                if total_bytes <= max_size_bytes:
                    break
                try:
                    f.unlink()
                    total_bytes -= size
                    freed_bytes += size
                    deleted_count += 1
                    logger.debug(f"[cache cleanup] 删除: {f.name}（{size} B）")
                except Exception as e:
                    logger.debug(f"[cache cleanup] 删除失败 {f}: {e}")

            remaining_mb = round(total_bytes / (1024 * 1024), 2)
            freed_mb = round(freed_bytes / (1024 * 1024), 2)
            logger.info(
                f"[cache cleanup] 完成：删除 {deleted_count} 个文件，"
                f"释放 {freed_mb} MB，剩余 {remaining_mb} MB"
            )
            return {
                'deleted_count': deleted_count,
                'freed_mb': freed_mb,
                'remaining_mb': remaining_mb,
            }

        except Exception as e:
            logger.error(f"按大小清理缓存失败: {e}")
            return {'deleted_count': 0, 'freed_mb': 0.0, 'remaining_mb': 0.0, 'error': str(e)}


# ============================================================================# 全局缩略图管理器实例
# ============================================================================

_thumbnail_manager = None


def get_thumbnail_manager() -> ThumbnailManager:
    """获取全局缩略图管理器实例"""
    global _thumbnail_manager
    if _thumbnail_manager is None:
        _thumbnail_manager = ThumbnailManager()
    return _thumbnail_manager
