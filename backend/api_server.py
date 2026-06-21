"""
Flask API 服务器 - Blur Arc 的 REST API 接口

提供以下功能：
- 相册统计信息获取
- 目录树遍历
- 照片列表获取
- 缩略图生成和缓存
- 照片导入
- 设置管理
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import json
import io
import os
import shutil
import sys
import urllib.parse
from pathlib import Path
from datetime import datetime
import threading
import logging
import uuid

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# 确保当前目录在 Python 路径中（为了导入同目录的模块）
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 共享常量和工具（延迟导入以兼容打包模式）
try:
    from .constants import MEDIA_FORMATS as _MEDIA_FORMATS, VIDEO_FORMATS as _VIDEO_FORMATS, IMAGE_FORMATS as _IMAGE_FORMATS
    from .utils import compute_md5 as _compute_md5
except ImportError:
    from constants import MEDIA_FORMATS as _MEDIA_FORMATS, VIDEO_FORMATS as _VIDEO_FORMATS, IMAGE_FORMATS as _IMAGE_FORMATS
    from utils import compute_md5 as _compute_md5

# 创建 Flask 应用
app = Flask(__name__)
# CORS：仅允许 PyWebView 和 localhost origin，防止恶意网站 CSRF
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            # PyWebView 使用特殊 origin，允许所有 PyWebView 请求
            "https://pywebview",
            # Android 模拟器通过 10.0.2.2 访问宿主机
            "http://10.0.2.2:5000",
        ],
        "supports_credentials": False,
    },
})

# ============================================================================
# 辅助函数
# ============================================================================

def get_config_manager():
    """获取配置管理器单例"""
    try:
        # 尝试相对导入（当作为模块被导入时）
        from .config_manager import get_config_manager as _get_cm
        return _get_cm()
    except ImportError:
        try:
            # 尝试绝对导入（当直接导入时）
            from config_manager import get_config_manager as _get_cm
            return _get_cm()
        except ImportError:
            logger.error("无法导入 ConfigManager")
            return None

def check_ffmpeg():
    """检查 FFmpeg 是否可用"""
    import sys
    import subprocess
    from pathlib import Path
    
    _EXE = ".exe" if sys.platform == "win32" else ""
    
    # 优先检查 backend/ffmpeg_binaries/（与 video_processor.py 保持一致）
    ffmpeg_bin_dir = Path(__file__).parent / "ffmpeg_binaries"
    local_ffmpeg = ffmpeg_bin_dir / f"ffmpeg{_EXE}"
    
    if local_ffmpeg.exists():
        try:
            result = subprocess.run([str(local_ffmpeg), '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                return True, str(local_ffmpeg)
        except Exception:
            pass
    
    # 回退：检查系统 PATH
    try:
        result = subprocess.run([f'ffmpeg{_EXE}', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True, 'system'
    except Exception:
        pass
    
    return False, None


def get_album_path():
    """获取相册路径"""
    config = get_config_manager()
    if config:
        return config.get_album_path()
    return None

def get_album_stats():
    """获取相册统计信息"""
    album_path = get_album_path()
    if not album_path or not Path(album_path).exists():
        return None
    
    album_path = Path(album_path)
    
    # 媒体格式分类（使用 constants 模块）
    VIDEO_FORMATS = _VIDEO_FORMATS
    MEDIA_FORMATS = _MEDIA_FORMATS
    
    years = {}
    
    # 优先从数据库获取准确的文件统计
    try:
        from database import SessionLocal, Photo
        db = SessionLocal()
        try:
            # 获取所有照片记录
            all_photos = db.query(Photo).all()
            album_path_resolved = str(Path(album_path).resolve()).lower()
            
            # 过滤出路径在相册目录下的照片
            valid_photos = []
            for photo in all_photos:
                try:
                    photo_path_resolved = str(Path(photo.path).resolve()).lower()
                    if photo_path_resolved.startswith(album_path_resolved):
                        valid_photos.append(photo)
                except Exception:
                    # 路径解析失败，跳过
                    pass
            
            # 只有当有有效照片记录时，才使用数据库统计
            if valid_photos:
                db_total_files = len(valid_photos)
                db_video_count = sum(1 for p in valid_photos if p.file_type == 'video')
                db_total_size = sum(p.size for p in valid_photos)
                logger.info(f'[get_album_stats] 数据库统计: {db_total_files} 个文件, {db_video_count} 个视频, {db_total_size} 字节')
            else:
                # 没有有效照片记录，使用文件系统统计
                db_total_files = None
                db_video_count = None
                db_total_size = None
                logger.info(f'[get_album_stats] 数据库中没有有效照片记录，将使用文件系统统计')
        finally:
            db.close()
    except Exception as e:
        logger.warning(f'[get_album_stats] 从数据库获取统计失败，将使用文件系统扫描: {e}')
        db_total_files = None
        db_video_count = None
        db_total_size = None
    
    # 文件系统遍历（用于获取目录结构）
    total_files = 0
    total_size = 0
    video_count = 0
    
    try:
        # 递归遍历所有目录
        def traverse_directory(directory, parent_info, rel_depth=0):
            nonlocal total_files, total_size, video_count
            
            dir_files = 0
            dir_size = 0
            sub_dirs = {}
            
            try:
                for item in sorted(directory.iterdir()):
                    if item.is_dir():
                        # 递归处理子目录
                        sub_dir_info = {}
                        sub_files, sub_size = traverse_directory(item, sub_dir_info, rel_depth + 1)
                        sub_dirs[item.name] = {
                            'count': sub_files,
                            'size': sub_size,
                            'subdirs': sub_dir_info
                        }
                        dir_files += sub_files
                        dir_size += sub_size
                    elif item.is_file():
                        ext = item.suffix.lower()
                        if ext not in MEDIA_FORMATS:
                            continue
                        # 处理文件
                        total_files += 1
                        if ext in VIDEO_FORMATS:
                            video_count += 1
                        file_size = item.stat().st_size
                        total_size += file_size
                        dir_files += 1
                        dir_size += file_size
            except Exception as e:
                logger.error(f"处理目录 {directory} 失败: {e}")
            
            return dir_files, dir_size
        
        # 遍历根目录下的所有目录
        for dir_item in sorted(album_path.iterdir()):
            if dir_item.is_dir():
                dir_info = {}
                dir_files, dir_size = traverse_directory(dir_item, dir_info, rel_depth=0)
                
                # 包含所有文件夹，即使没有照片
                years[dir_item.name] = {
                    'count': dir_files,
                    'size': dir_size,
                    'subdirs': dir_info
                }
            elif dir_item.is_file():
                # 处理根目录下的文件
                ext = dir_item.suffix.lower()
                if ext in MEDIA_FORMATS:
                    total_files += 1
                    if ext in VIDEO_FORMATS:
                        video_count += 1
                    total_size += dir_item.stat().st_size
                
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        # 发生异常时返回空统计对象，而不是 None
        return {
            'total_files': 0,
            'video_count': 0,
            'total_size': 0,
            'total_size_mb': 0.0,
            'years': {}
        }
    
    # 始终使用文件系统统计（更准确，反映实际文件数量）
    # 数据库统计仅作为备用（当文件系统扫描失败时）
    final_total_files = total_files if total_files > 0 else (db_total_files or 0)
    final_video_count = video_count if total_files > 0 else (db_video_count or 0)
    final_total_size = total_size if total_files > 0 else (db_total_size or 0)

    return {
        'total_files': final_total_files,
        'video_count': final_video_count,
        'total_size': final_total_size,
        'total_size_mb': round(final_total_size / (1024 * 1024), 2),
        'years': years
    }

# ============================================================================
# API 路由
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    logger.info('[API] 💚 健康检查请求')
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/album/stats', methods=['GET'])
def album_stats():
    """获取相册统计信息"""
    logger.info('[API] 📊 相册统计请求')
    try:
        stats = get_album_stats()
        if stats is None:
            logger.error('[API] 📊 无法获取相册统计信息')
            return jsonify({'error': '无法获取相册统计信息'}), 500
        
        # 添加最后导入时间
        config = get_config_manager()
        if config:
            last_import = config.get_last_import()
            stats['last_import'] = last_import
        else:
            stats['last_import'] = None
        
        logger.info(f'[API] 📊 统计结果: {stats["total_files"]} 个文件, {stats["total_size_mb"]} MB, 最后导入: {stats.get("last_import")}')
        return jsonify(stats)
    except Exception as e:
        logger.error(f"[API] ❌ /api/album/stats 错误: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/album/tree', methods=['GET'])
def album_tree():
    """获取完整目录树"""
    logger.info('[API] 🌳 目录树请求')
    try:
        album_path = get_album_path()
        logger.info(f'[API] 🌳 相册路径: {album_path}')
        
        if not album_path or not Path(album_path).exists():
            logger.error(f'[API] 🌳 相册路径不存在: {album_path}')
            return jsonify({'error': '相册路径不存在'}), 404
        
        # 迭代构建目录树（纯文件系统扫描，不依赖数据库）
        # 目录层级和命名不固定，直接从文件系统读取
        def build_tree(directory):
            """
            优化点：
            1. 使用迭代方式替代递归，避免栈溢出风险
            2. 使用os.scandir替代pathlib.iterdir，减少系统调用
            3. 纯文件系统扫描，支持任意目录结构
            4. 从深层目录开始处理，确保计数正确累加
            """
            import os
            
            # 支持的媒体格式（使用 constants 模块）
            MEDIA_FORMATS = _MEDIA_FORMATS
            
            directory_str = str(directory)
            root_node = {
                'name': directory.name,
                'path': directory_str,
                'type': 'root',
                'count': 0,
                'children': []
            }
            
            # 使用栈存储待处理的目录
            # 每个栈元素是 (目录路径, 父节点, 子节点, 是否已处理)
            stack = []
            
            # 先处理根目录的直接子目录
            try:
                with os.scandir(directory_str) as entries:
                    # 先收集所有条目并分类
                    dir_entries = []
                    file_count = 0
                    
                    for entry in entries:
                        if entry.is_dir(follow_symlinks=False):
                            dir_entries.append(entry)
                        elif entry.is_file(follow_symlinks=False):
                            # 只计数媒体文件
                            if os.path.splitext(entry.name)[1].lower() in MEDIA_FORMATS:
                                file_count += 1
                    
                    # 对子目录进行排序
                    dir_entries.sort(key=lambda x: x.name)
                    
                    # 根目录的文件计数（直接从文件系统扫描）
                    root_node['count'] = file_count
                    
                    # 为每个子目录创建节点并添加到栈中
                    for dir_entry in dir_entries:
                        child_node = {
                            'name': dir_entry.name,
                            'path': dir_entry.path,
                            'type': 'directory',
                            'count': 0,  # 初始为0，稍后从文件系统扫描
                            'children': []
                        }
                        root_node['children'].append(child_node)
                        # 将子目录加入栈中，标记为未处理
                        stack.append((dir_entry.path, root_node, child_node, False))
            except Exception as e:
                logger.error(f"处理根目录 {directory_str} 时出错: {e}")
                return root_node
            
            # 处理栈中的所有目录
            while stack:
                current_path, parent_node, current_node, processed = stack.pop()
                
                if not processed:
                    # 第一次处理：收集所有子目录和文件计数
                    try:
                        with os.scandir(current_path) as entries:
                            dir_entries = []
                            file_count = 0
                            
                            for entry in entries:
                                if entry.is_dir(follow_symlinks=False):
                                    dir_entries.append(entry)
                                elif entry.is_file(follow_symlinks=False):
                                    # 只计数媒体文件
                                    if os.path.splitext(entry.name)[1].lower() in MEDIA_FORMATS:
                                        file_count += 1
                            
                            # 对子目录进行排序
                            dir_entries.sort(key=lambda x: x.name)
                            
                            # 设置当前节点的文件计数（直接从文件系统扫描）
                            current_node['count'] = file_count
                            
                            # 标记当前节点为已处理
                            stack.append((current_path, parent_node, current_node, True))
                            
                            # 为每个子目录创建节点并添加到栈中
                            for dir_entry in dir_entries:
                                child_node = {
                                    'name': dir_entry.name,
                                    'path': dir_entry.path,
                                    'type': 'directory',
                                    'count': 0,  # 初始为0，稍后从文件系统扫描
                                    'children': []
                                }
                                current_node['children'].append(child_node)
                                # 将子目录加入栈中，标记为未处理
                                stack.append((dir_entry.path, current_node, child_node, False))
                    except Exception as e:
                        logger.error(f"处理目录 {current_path} 时出错: {e}")
                else:
                    # 第二次处理：自下而上累加子目录计数
                    for child in current_node['children']:
                        current_node['count'] += child['count']
            
            return root_node
        
        # 构建完整树
        tree_data = build_tree(Path(album_path))
        
        # 根节点的总文件数 = 根目录下的文件数 + 所有子节点的文件数
        # build_tree 中已经设置了根目录下的文件数，这里只需要加上子节点的累加
        children_count = sum(child.get('count', 0) for child in tree_data.get('children', []))
        tree_data['count'] = tree_data.get('count', 0) + children_count
        
        logger.info(f'[API] 🌳 目录树构建完成: {len(tree_data["children"])} 个子目录')
        logger.info(f'[API] 🌳 根节点计数: {tree_data["count"]}')
        return jsonify(tree_data)
    except Exception as e:
        logger.error(f"[API] ❌ /api/album/tree 错误: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/album/photos', methods=['GET'])
def album_photos():
    """获取指定路径下的照片列表（支持分页）"""
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': '缺少 path 参数'}), 400
        
        # 分页参数
        page = int(request.args.get('page', '1'))
        page_size = int(request.args.get('page_size', '100'))
        
        target_path = Path(path)
        if not target_path.exists() or not target_path.is_dir():
            return jsonify({'error': f'目录不存在: {path}'}), 404
        
        # 安全检查：确保请求路径在相册目录内（防目录遍历攻击）
        album_path = get_album_path()
        if album_path:
            try:
                target_path.resolve().relative_to(Path(album_path).resolve())
            except ValueError:
                logger.warning(f"拒绝访问相册目录外的路径: {path}")
                return jsonify({'error': '访问被拒绝：目录不在相册范围内'}), 403
        
        # 支持的媒体格式（使用 constants 模块）
        MEDIA_FORMATS = _MEDIA_FORMATS
        
        # 收集所有媒体文件
        all_files = []
        for file in sorted(target_path.iterdir()):
            if file.is_file() and file.suffix.lower() in MEDIA_FORMATS:
                all_files.append(file)
        
        # 分页计算
        total_count = len(all_files)
        total_pages = (total_count + page_size - 1) // page_size
        
        # 边界检查
        if page < 1:
            page = 1
        if page > total_pages:
            photos = []
        else:
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_files = all_files[start_idx:end_idx]
            
            photos = []
            for file in page_files:
                stat = file.stat()
                encoded_path = urllib.parse.quote(str(file))
                file_type = 'photo' if file.suffix.lower() in _IMAGE_FORMATS else 'video'
                photos.append({
                    'id': str(file),
                    'name': file.name,
                    'path': str(file),
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'date': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'type': file_type,
                    'thumbnail_url': f'/api/album/thumbnail?path={encoded_path}',
                    'url': f'/api/album/file?path={encoded_path}',
                    # preview_url: 视频用 file 路由，图片用专用 preview 路由（支持 HEIC 等格式转换）
                    'preview_url': f'/api/album/file?path={encoded_path}' if file_type == 'video' else f'/api/album/preview?path={encoded_path}',
                })
        
        return jsonify({
            'path': str(target_path),
            'count': total_count,
            'total_pages': total_pages,
            'page': page,
            'page_size': page_size,
            'photos': photos
        })
    except Exception as e:
        logger.error(f"API 错误 /api/album/photos: {e}")
        return jsonify({'error': str(e)}), 500

try:
    from .thumbnail_manager import get_thumbnail_manager
except ImportError:
    from thumbnail_manager import get_thumbnail_manager


@app.route('/api/album/thumbnail', methods=['GET'])
def album_thumbnail():
    """获取照片缩略图（带缓存机制）"""
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': '缺少 path 参数'}), 400
        
        # 解码URL编码的路径
        path = urllib.parse.unquote(path)
        
        # 获取缩略图管理器
        thumbnail_manager = get_thumbnail_manager()
        
        # 同步获取缩略图
        thumbnail_path = thumbnail_manager.get_thumbnail_sync(path)
        
        if thumbnail_path:
            return send_file(str(thumbnail_path), mimetype='image/jpeg')
        else:
            return jsonify({'error': '无法生成缩略图'}), 400
            
    except Exception as e:
        logger.error(f"API 错误 /api/album/thumbnail: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/album/file', methods=['GET'])
def album_file():
    """提供原图文件访问（支持 HTTP Range，视频 seek 必须）"""
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': '缺少 path 参数'}), 400
        
        path = urllib.parse.unquote(path)
        file_path = Path(path)
        
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'error': f'文件不存在: {path}'}), 404
        
        # 安全检查：确保文件在相册目录内
        album_path = get_album_path()
        if album_path:
            try:
                file_path.resolve().relative_to(Path(album_path).resolve())
            except ValueError:
                return jsonify({'error': '访问被拒绝：文件不在相册目录内'}), 403
        
        # 根据扩展名确定 MIME 类型
        ext = file_path.suffix.lower()
        mime_map = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.gif': 'image/gif',
            '.webp': 'image/webp', '.bmp': 'image/bmp',
            '.tiff': 'image/tiff', '.heic': 'image/heic',
            '.mp4': 'video/mp4', '.mkv': 'video/x-matroska',
            '.avi': 'video/x-msvideo', '.mov': 'video/quicktime',
            '.wmv': 'video/x-ms-wmv', '.webm': 'video/webm',
            '.m4v': 'video/mp4', '.flv': 'video/x-flv',
            '.mpg': 'video/mpeg', '.mpeg': 'video/mpeg',
            '.3gp': 'video/3gpp',
        }
        mimetype = mime_map.get(ext, 'application/octet-stream')
        
        # conditional=True 让 Flask 自动处理 Range / If-Range 请求头，视频 seek 需要
        return send_file(str(file_path), mimetype=mimetype, conditional=True)
    except Exception as e:
        logger.error(f"API 错误 /api/album/file: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/album/exif', methods=['GET'])
def album_exif():
    """读取图片 EXIF 元数据，返回结构化 JSON。
    
    Query params:
        path (str): 图片文件的绝对路径（URL 编码）
    
    Returns:
        JSON {
          make, model, datetime_original,
          focal_length, f_number, exposure_time, iso,
          image_width, image_height,
          gps: {lat, lng} | None
        }
    """
    from fractions import Fraction

    file_path = request.args.get('path', '')
    if not file_path:
        return jsonify({'error': '缺少 path 参数'}), 400

    path = Path(file_path)
    if not path.exists():
        return jsonify({'error': '文件不存在'}), 404

    # 路径安全检查（防止越界）
    album_path = get_album_path()
    if album_path:
        try:
            path.resolve().relative_to(Path(album_path).resolve())
        except ValueError:
            return jsonify({'error': '路径越界'}), 403

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS

        img = Image.open(path)
        raw_exif = img._getexif()
        if not raw_exif:
            return jsonify({})

        # 将数字 tag_id → 可读名称
        exif = {TAGS.get(k, k): v for k, v in raw_exif.items()}

        def _rational(val):
            """将 IFDRational / tuple / float 转为 float，失败返回 None"""
            try:
                if hasattr(val, 'numerator') and hasattr(val, 'denominator'):
                    return float(val.numerator) / float(val.denominator) if float(val.denominator) != 0 else None
                if isinstance(val, tuple) and len(val) == 2:
                    return float(val[0]) / float(val[1]) if val[1] != 0 else None
                return float(val)
            except Exception:
                return None

        # 基本信息
        result = {
            'make':             str(exif.get('Make', '') or '').strip(),
            'model':            str(exif.get('Model', '') or '').strip(),
            'datetime_original': str(exif.get('DateTimeOriginal', '') or '').strip(),
            'image_width':      exif.get('ExifImageWidth') or exif.get('ImageWidth'),
            'image_height':     exif.get('ExifImageHeight') or exif.get('ImageLength'),
        }

        # 焦距（mm）
        fl = _rational(exif.get('FocalLength'))
        result['focal_length'] = f"{fl:.1f}mm" if fl is not None else None

        # 等效焦距（35mm）
        fl35 = _rational(exif.get('FocalLengthIn35mmFilm'))
        result['focal_length_35mm'] = f"{fl35:.0f}mm" if fl35 is not None else None

        # 光圈 f/N
        fn = _rational(exif.get('FNumber'))
        result['f_number'] = f"f/{fn:.1f}" if fn is not None else None

        # 快门速度
        et = _rational(exif.get('ExposureTime'))
        if et is not None:
            if et < 1:
                # 显示分数形式，如 1/125s
                denom = round(1 / et)
                result['exposure_time'] = f"1/{denom}s"
            else:
                result['exposure_time'] = f"{et:.1f}s"
        else:
            result['exposure_time'] = None

        # ISO
        result['iso'] = exif.get('ISOSpeedRatings') or exif.get('ISO')

        # 曝光补偿
        eb = _rational(exif.get('ExposureBiasValue'))
        result['exposure_bias'] = f"{eb:+.1f}EV" if eb is not None else None

        # 白平衡
        wb_map = {0: '自动', 1: '手动'}
        result['white_balance'] = wb_map.get(exif.get('WhiteBalance'), None)

        # 闪光灯
        flash_val = exif.get('Flash')
        result['flash'] = '开' if flash_val and (flash_val & 0x1) else '关' if flash_val is not None else None

        # GPS
        gps_info = exif.get('GPSInfo')
        result['gps'] = None
        if gps_info and isinstance(gps_info, dict):
            try:
                gps = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}
                def _dms_to_deg(dms):
                    d = _rational(dms[0])
                    m = _rational(dms[1])
                    s = _rational(dms[2])
                    if None not in (d, m, s):
                        return d + m / 60 + s / 3600
                    return None
                lat = _dms_to_deg(gps.get('GPSLatitude', []))
                lng = _dms_to_deg(gps.get('GPSLongitude', []))
                if lat is not None and lng is not None:
                    if gps.get('GPSLatitudeRef') == 'S':
                        lat = -lat
                    if gps.get('GPSLongitudeRef') == 'W':
                        lng = -lng
                    result['gps'] = {'lat': round(lat, 6), 'lng': round(lng, 6)}
            except Exception:
                pass

        # 清理空字符串
        for k in ('make', 'model', 'datetime_original'):
            if result.get(k) == '':
                result[k] = None

        return jsonify(result)

    except Exception as e:
        logger.warning(f"读取 EXIF 失败 {path}: {e}")
        return jsonify({}), 200  # 静默失败，前端不显示面板


@app.route('/api/album/preview', methods=['GET'])
def album_preview():
    """提供适合浏览器预览的图片文件。
    
    对于浏览器原生支持的格式（jpg/png/gif/webp），直接返回原文件。
    对于 HEIC/TIFF/BMP/ICO 等格式，转换为 JPEG 后返回（结果缓存到磁盘）。
    """
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': '缺少 path 参数'}), 400

        path = urllib.parse.unquote(path)
        file_path = Path(path)

        if not file_path.exists() or not file_path.is_file():
            return jsonify({'error': f'文件不存在: {path}'}), 404

        # 安全检查
        album_path = get_album_path()
        if album_path:
            try:
                file_path.resolve().relative_to(Path(album_path).resolve())
            except ValueError:
                return jsonify({'error': '访问被拒绝：文件不在相册目录内'}), 403

        thumbnail_manager = get_thumbnail_manager()
        preview_path = thumbnail_manager.get_preview_jpeg(str(file_path))

        if preview_path is None:
            # 无法转换（视频或不支持的格式），回落到原文件
            logger.warning(f"[preview] 无法生成预览图，回落到原文件: {file_path}")
            return send_file(str(file_path), conditional=True)

        # 判断返回的是原文件还是转换后的缓存文件
        if Path(preview_path) == file_path:
            # 原生格式直接返回
            ext = file_path.suffix.lower()
            mime_map = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.gif': 'image/gif',
                '.webp': 'image/webp',
            }
            mimetype = mime_map.get(ext, 'image/jpeg')
            return send_file(str(preview_path), mimetype=mimetype, conditional=True)
        else:
            # 转换后的 JPEG 缓存
            return send_file(str(preview_path), mimetype='image/jpeg', conditional=True)

    except Exception as e:
        logger.error(f"API 错误 /api/album/preview: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/video/metadata', methods=['GET'])
def video_metadata():
    """提取视频元数据（时长、分辨率、编码等）"""
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': '缺少 path 参数'}), 400

        path = urllib.parse.unquote(path)
        file_path = Path(path)

        if not file_path.exists() or not file_path.is_file():
            return jsonify({'error': f'文件不存在: {path}'}), 404

        # 安全检查
        album_path = get_album_path()
        if album_path:
            try:
                file_path.resolve().relative_to(Path(album_path).resolve())
            except ValueError:
                return jsonify({'error': '访问被拒绝：文件不在相册目录内'}), 403

        # 使用 VideoProcessor 提取元数据
        try:
            from .video_processor import VideoProcessor
        except ImportError:
            from video_processor import VideoProcessor

        metadata = VideoProcessor.extract_metadata(str(file_path))

        if metadata is None:
            return jsonify({
                'available': False,
                'message': 'FFmpeg 不可用或无法提取元数据'
            })

        # 格式化时长
        duration_sec = metadata.get('duration', 0)
        duration_fmt = ''
        if duration_sec:
            h = int(duration_sec // 3600)
            m = int((duration_sec % 3600) // 60)
            s = int(duration_sec % 60)
            if h > 0:
                duration_fmt = f"{h:02d}:{m:02d}:{s:02d}"
            else:
                duration_fmt = f"{m:02d}:{s:02d}"

        width  = metadata.get('width', 0)
        height = metadata.get('height', 0)
        result = {
            'available': True,
            'duration': duration_sec,
            'duration_formatted': duration_fmt if duration_sec else '',
            'width': width,
            'height': height,
            # 只有宽高都有效时才填写 resolution，避免前端显示 "0×0"
            'resolution': f"{width}×{height}" if width and height else '',
            'codec': metadata.get('codec', ''),
            'format': metadata.get('format', ''),
            'size': metadata.get('size', 0),
        }
        return jsonify(result)

    except Exception as e:
        logger.error(f"API 错误 /api/video/metadata: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/album-path', methods=['GET'])
def get_album_path_api():
    """获取当前相册路径"""
    try:
        album_path = get_album_path()
        logger.info(f"[API] 📁 获取相册路径: {album_path}")
        # 确保返回的是None而不是空字符串
        return jsonify({
            'album_path': album_path if album_path else None
        })
    except Exception as e:
        logger.error(f"API 错误 /api/settings/album-path: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/album-path', methods=['PUT'])
def set_album_path_api():
    """修改相册路径（异步版）
    
    立即返回 task_id，MD5 索引重建在后台线程执行。
    前端通过 GET /api/settings/rebuild-progress/<task_id> 轮询进度。
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        new_path = data.get('album_path')
        
        if not new_path:
            return jsonify({'error': '缺少 album_path 参数'}), 400
        
        new_path = Path(new_path)
        if not new_path.exists():
            return jsonify({'error': f'路径不存在: {new_path}'}), 404
        
        if not new_path.is_dir():
            return jsonify({'error': f'路径不是目录: {new_path}'}), 400
        
        config = get_config_manager()
        if not config:
            return jsonify({'error': '配置管理器初始化失败'}), 500
        
        new_path_abs = str(new_path.absolute())
        
        # 只做配置写入（快，同步），跳过耗时的 MD5 重建
        try:
            success = config.set_album_path_only(new_path_abs)
        except AttributeError:
            # 兼容旧版：直接调用同步方法（会阻塞，但不至于崩溃）
            success = config.set_album_path(new_path_abs)
        
        if not success:
            return jsonify({'error': '设置相册路径失败'}), 500
        
        # 生成任务 ID，后台线程执行重建
        task_id = f"rebuild_{uuid.uuid4().hex[:8]}"
        with _rebuild_lock:
            _rebuild_tasks[task_id] = {
                'status': 'running',
                'album_path': new_path_abs,
                'message': '正在扫描相册...',
                'progress': 0,
            }
        
        def _do_rebuild(tid, path_abs):
            def _ttl_cleanup():
                with _rebuild_lock:
                    _rebuild_tasks.pop(tid, None)
                logger.debug(f"[rebuild] 任务 {tid} TTL 已清理")

            try:
                cfg = get_config_manager()
                # 执行重建（通知进度）
                def on_progress(msg, pct):
                    with _rebuild_lock:
                        if tid in _rebuild_tasks:
                            _rebuild_tasks[tid]['message'] = msg
                            _rebuild_tasks[tid]['progress'] = pct
                
                on_progress('正在清空旧索引...', 5)
                cfg._rebuild_md5_index_for_album(Path(path_abs), progress_cb=on_progress)
                
                with _rebuild_lock:
                    _rebuild_tasks[tid]['status'] = 'done'
                    _rebuild_tasks[tid]['message'] = '索引重建完成'
                    _rebuild_tasks[tid]['progress'] = 100
                logger.info(f"[rebuild] 任务 {tid} 完成")
            except Exception as e:
                logger.error(f"[rebuild] 任务 {tid} 失败: {e}")
                with _rebuild_lock:
                    _rebuild_tasks[tid]['status'] = 'error'
                    _rebuild_tasks[tid]['message'] = str(e)
            finally:
                # 5 分钟后自动清理任务条目，防止内存泄漏
                t_cleanup = threading.Timer(300, _ttl_cleanup)
                t_cleanup.daemon = True
                t_cleanup.start()
        
        t = threading.Thread(target=_do_rebuild, args=(task_id, new_path_abs), daemon=True)
        t.start()
        
        return jsonify({
            'status': 'rebuilding',
            'album_path': new_path_abs,
            'task_id': task_id,
        })
    
    except Exception as e:
        logger.error(f"API 错误 PUT /api/settings/album-path: {e}")
        return jsonify({'error': str(e)}), 500


# 重建任务状态存储
_rebuild_tasks: dict = {}
_rebuild_lock = threading.Lock()


@app.route('/api/settings/rebuild-progress/<task_id>', methods=['GET'])
def get_rebuild_progress(task_id):
    """查询相册 MD5 索引重建进度

    返回:
      status: running | done | error
      progress: 0-100
      message: 当前步骤描述
    """
    with _rebuild_lock:
        task = _rebuild_tasks.get(task_id)

    if not task:
        return jsonify({'error': '任务不存在'}), 404

    return jsonify(task)


@app.route('/api/settings/rebuild-index', methods=['POST'])
def rebuild_index():
    """强制重建相册索引（数据库 + 清空缩略图缓存）

    用于手动刷新数据库记录和清理缩略图缓存。

    返回:
      task_id: 任务 ID，用于查询进度
      status: started
    """
    try:
        album_path = get_album_path()
        if not album_path:
            return jsonify({'error': '未设置相册路径'}), 400

        album_path_abs = str(Path(album_path).absolute())

        # 清空缩略图缓存
        tm = get_thumbnail_manager()
        cache_cleared = 0
        try:
            for cache_file in tm.cache_dir.glob('*.jpg'):
                cache_file.unlink()
                cache_cleared += 1
            logger.info(f"[rebuild] 已清空 {cache_cleared} 个缩略图缓存")
        except Exception as e:
            logger.warning(f"[rebuild] 清空缩略图缓存失败: {e}")

        # 生成任务 ID，后台线程执行重建
        task_id = f"rebuild_{uuid.uuid4().hex[:8]}"
        with _rebuild_lock:
            _rebuild_tasks[task_id] = {
                'status': 'running',
                'album_path': album_path_abs,
                'message': '正在重建索引...',
                'progress': 0,
            }

        def _do_rebuild(tid, path_abs):
            def _ttl_cleanup():
                with _rebuild_lock:
                    _rebuild_tasks.pop(tid, None)
                logger.debug(f"[rebuild] 任务 {tid} TTL 已清理")

            def on_progress(msg, pct):
                with _rebuild_lock:
                    if tid in _rebuild_tasks:
                        _rebuild_tasks[tid]['message'] = msg
                        _rebuild_tasks[tid]['progress'] = pct

            try:
                cfg = get_config_manager()
                cfg._rebuild_md5_index_for_album(Path(path_abs), progress_cb=on_progress)

                with _rebuild_lock:
                    _rebuild_tasks[tid]['status'] = 'done'
                    _rebuild_tasks[tid]['message'] = '索引重建完成'
                    _rebuild_tasks[tid]['progress'] = 100
                logger.info(f"[rebuild] 任务 {tid} 完成")
            except Exception as e:
                logger.error(f"[rebuild] 任务 {tid} 失败: {e}")
                with _rebuild_lock:
                    _rebuild_tasks[tid]['status'] = 'error'
                    _rebuild_tasks[tid]['message'] = str(e)

            # 5 分钟后自动清理任务记录
            t_cleanup = threading.Timer(300, _ttl_cleanup)
            t_cleanup.daemon = True
            t_cleanup.start()

        t = threading.Thread(target=_do_rebuild, args=(task_id, album_path_abs), daemon=True)
        t.start()

        return jsonify({
            'status': 'started',
            'task_id': task_id,
            'cache_cleared': cache_cleared
        })
    except Exception as e:
        logger.error(f"API 错误 POST /api/settings/rebuild-index: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/settings/ffmpeg-status', methods=['GET'])
def get_ffmpeg_status():
    """获取 FFmpeg 状态"""
    try:
        logger.info('[API] 🔍 检查 FFmpeg 状态')
        available, path = check_ffmpeg()
        
        status = 'available' if available else 'unavailable'
        
        logger.info(f'[API] 📊 FFmpeg 状态: {status}, 路径: {path}')
        
        return jsonify({
            'status': status,
            'path': path,
            'message': 'FFmpeg 已就绪' if available else 'FFmpeg 未安装'
        })
    except Exception as e:
        logger.error(f"[API] ❌ 检查 FFmpeg 状态失败: {e}")
        return jsonify({
            'status': 'error',
            'message': f'检查 FFmpeg 状态失败: {e}'
        }), 500

@app.route('/api/system/locale', methods=['GET'])
def get_system_locale():
    """检测操作系统首选语言
    
    Returns:
        locale: 系统 locale 字符串（如 zh_CN、en_US）
        language: 推荐语言代码，'zh' 或 'en'
    """
    try:
        import locale as _locale
        import sys

        system_locale = ''

        if sys.platform == 'win32':
            # Windows：优先用 GetUserDefaultLocaleName（更准确）
            try:
                import ctypes
                buf = ctypes.create_unicode_buffer(85)
                ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85)
                system_locale = buf.value  # 例如 'zh-CN'、'en-US'
            except Exception:
                pass

        if not system_locale:
            # 跨平台回退：python locale 模块
            try:
                loc = _locale.getdefaultlocale()
                system_locale = loc[0] or ''
            except Exception:
                system_locale = ''

        # 规范化：zh-CN / zh_CN / zh → 'zh'；其余默认 'en'
        lang = system_locale.lower().replace('-', '_').split('_')[0]
        recommended = 'zh' if lang == 'zh' else 'en'

        logger.info(f'[API] 系统语言检测: locale={system_locale!r}, recommended={recommended}')
        return jsonify({
            'locale': system_locale,
            'language': recommended
        })
    except Exception as e:
        logger.error(f'[API] 系统语言检测失败: {e}')
        return jsonify({'locale': '', 'language': 'zh'}), 200  # 降级中文


@app.route('/api/settings/language', methods=['GET'])
def get_language():
    """获取用户语言偏好"""
    try:
        cm = get_config_manager()
        lang = cm.get_setting('language', None)
        return jsonify({'language': lang})
    except Exception as e:
        logger.error(f'[API] 获取语言偏好失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/language', methods=['PUT'])
def set_language():
    """保存用户语言偏好（'zh' 或 'en'）"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        lang = data.get('language', 'zh')
        if lang not in ('zh', 'en'):
            return jsonify({'error': '不支持的语言代码，仅支持 zh 或 en'}), 400
        cm = get_config_manager()
        cm.update_setting('language', lang)
        logger.info(f'[API] 语言偏好已保存: {lang}')
        return jsonify({'status': 'ok', 'language': lang})
    except Exception as e:
        logger.error(f'[API] 保存语言偏好失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/theme', methods=['GET'])
def get_theme():
    """获取用户主题偏好"""
    try:
        cm = get_config_manager()
        theme = cm.get_setting('theme', 'system')
        return jsonify({'theme': theme})
    except Exception as e:
        logger.error(f'[API] 获取主题偏好失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/theme', methods=['PUT'])
def set_theme():
    """保存用户主题偏好（'light' / 'dark' / 'system'）"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        theme = data.get('theme', 'system')
        if theme not in ('light', 'dark', 'system'):
            return jsonify({'error': '不支持的主题，仅支持 light / dark / system'}), 400
        cm = get_config_manager()
        cm.update_setting('theme', theme)
        logger.info(f'[API] 主题偏好已保存: {theme}')
        return jsonify({'status': 'ok', 'theme': theme})
    except Exception as e:
        logger.error(f'[API] 保存主题偏好失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/test', methods=['GET'])
def test_api():
    """测试 API"""
    return jsonify({
        'message': 'API 工作正常',
        'timestamp': datetime.now().isoformat()
    })


# ============================================================================
# 手机上传 API
# ============================================================================

# 手机上传服务器（延迟初始化）
_phone_upload_server = None

def _get_phone_upload_server():
    """获取手机上传服务器单例"""
    global _phone_upload_server
    if _phone_upload_server is None:
        try:
            from .phone_upload_server import PhoneUploadServer
        except ImportError:
            from phone_upload_server import PhoneUploadServer
        _phone_upload_server = PhoneUploadServer()
    return _phone_upload_server


@app.route('/api/phone-upload/start', methods=['POST'])
def phone_upload_start():
    """启动手机上传服务器"""
    try:
        server = _get_phone_upload_server()
        info = server.start()
        return jsonify(info)
    except Exception as e:
        logger.error(f'[API] 启动手机上传服务器失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/phone-upload/stop', methods=['POST'])
def phone_upload_stop():
    """停止手机上传服务器（保留已上传文件）"""
    try:
        server = _get_phone_upload_server()
        server.stop(cleanup=False)
        return jsonify({'status': 'stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phone-upload/status', methods=['GET'])
def phone_upload_status():
    """获取上传进度"""
    try:
        server = _get_phone_upload_server()
        session = server.get_session()
        if not session:
            return jsonify({'error': '没有活跃的会话'}), 404
        return jsonify(session.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phone-upload/qr', methods=['GET'])
def phone_upload_qr():
    """获取二维码 PNG 图片"""
    try:
        server = _get_phone_upload_server()
        png_data = server.get_qr_png()
        return send_file(
            io.BytesIO(png_data),
            mimetype='image/png',
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phone-upload/incomplete', methods=['GET'])
def phone_upload_incomplete():
    """检查是否有未完成的会话"""
    try:
        server = _get_phone_upload_server()
        session = server.has_incomplete_session()
        return jsonify({'session': session})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phone-upload/resume', methods=['POST'])
def phone_upload_resume():
    """恢复未完成的会话"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        session_id = data.get('session_id', '')
        if not session_id:
            return jsonify({'error': '缺少 session_id'}), 400

        server = _get_phone_upload_server()
        session = server.resume_session(session_id)
        if not session:
            return jsonify({'error': '会话不存在或已完成'}), 404

        info = server.start(session=session)
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phone-upload/discard', methods=['POST'])
def phone_upload_discard():
    """放弃未完成的会话并清理文件（需提供 session_id 作为二次确认）"""
    try:
        from .phone_upload_server import UPLOAD_ROOT, SESSIONS_FILE
    except ImportError:
        from phone_upload_server import UPLOAD_ROOT, SESSIONS_FILE

    # 二次确认：必须提供 session_id，防止误触/CSRF 删除
    data = request.get_json(force=True, silent=True) or {}
    session_id = data.get('session_id', '')
    if not session_id:
        return jsonify({'error': '缺少 session_id 参数'}), 400

    try:
        server = _get_phone_upload_server()
        incomplete = server.has_incomplete_session()
        if incomplete and incomplete.get("id") == session_id:
            session_dir = UPLOAD_ROOT / incomplete["upload_dir"]
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            # Remove from sessions.json
            if SESSIONS_FILE.exists():
                data_json = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
                data_json["sessions"] = [
                    s for s in data_json.get("sessions", [])
                    if s.get("id") != session_id
                ]
                SESSIONS_FILE.write_text(
                    json.dumps(data_json, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
        else:
            return jsonify({'error': '会话不存在或 session_id 不匹配'}), 404
        return jsonify({'status': 'discarded'})
    except Exception as e:
        logger.error(f'[API] 放弃上传会话失败: {e}')
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 移动接入 API
# ============================================================================

_mobile_access_server = None

# Flutter App 上传通知 — mobile_access_server 调用此函数，前端轮询取
_flutter_upload_sessions: dict[str, dict] = {}
_flutter_upload_lock = threading.Lock()

def _notify_flutter_upload(device_name: str, upload_dir: str, file_count: int):
    """记录一次 Flutter App 文件上传事件，供前端轮询弹窗"""
    with _flutter_upload_lock:
        _flutter_upload_sessions[upload_dir] = {
            "device_name": device_name,
            "upload_dir": upload_dir,
            "file_count": file_count,
            "updated_at": datetime.now().isoformat(),
        }

def _get_mobile_server():
    global _mobile_access_server
    if _mobile_access_server is None:
        try:
            from .mobile_access_server import MobileAccessServer
        except ImportError:
            from mobile_access_server import MobileAccessServer
        _mobile_access_server = MobileAccessServer()
    return _mobile_access_server


@app.route('/api/mobile/status', methods=['GET'])
def mobile_status():
    """获取移动接入服务状态"""
    try:
        server = _get_mobile_server()
        cm = get_config_manager()
        enabled = cm.get_setting('mobile_service_enabled', False) if cm else False
        return jsonify({
            'enabled': bool(enabled),
            'running': server.port is not None,
            'port': server.port,
            'local_ip': server._local_ip if server.port else None,
            'paired_count': len(server.token_manager.get_paired_devices()) if server.port else 0,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/enable', methods=['POST'])
def mobile_enable():
    """启用移动接入服务"""
    try:
        server = _get_mobile_server()
        info = server.start()
        cm = get_config_manager()
        if cm:
            cm.update_setting('mobile_service_enabled', True)
        return jsonify({'status': 'enabled', **info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/disable', methods=['POST'])
def mobile_disable():
    """停止移动接入服务（保留已配对设备的 token，下次开启时可继续使用）"""
    try:
        server = _get_mobile_server()
        server.stop()
        cm = get_config_manager()
        if cm:
            cm.update_setting('mobile_service_enabled', False)
        return jsonify({'status': 'disabled'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/qr', methods=['GET'])
def mobile_qr():
    """获取移动配对二维码 PNG"""
    try:
        from .mobile_access_server import generate_mobile_qr
        server = _get_mobile_server()
        code, _ = server.token_manager.generate_pairing_code()
        png = generate_mobile_qr(code, server._local_ip, server.port)
        return send_file(io.BytesIO(png), mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/pending-request', methods=['GET'])
def mobile_pending_request():
    """获取当前待配对请求"""
    try:
        server = _get_mobile_server()
        code = server.token_manager.get_pending_pair_code()
        if code:
            device_name = server.token_manager.get_pending_device_name(code)
            return jsonify({'hasPending': True, 'pairing_code': code, 'device_name': device_name})
        return jsonify({'hasPending': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/confirm-pairing', methods=['POST'])
def mobile_confirm_pairing():
    """确认或拒绝配对请求"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        code = data.get('pairing_code', '')
        action = data.get('action', '')
        server = _get_mobile_server()
        if action == 'accept':
            token = server.token_manager.confirm_pair_request(code)
            if token:
                return jsonify({'status': 'accepted'})
            return jsonify({'error': '配对码无效或已过期'}), 400
        else:
            server.token_manager.reject_pair_request(code)
            return jsonify({'status': 'rejected'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/devices', methods=['GET'])
def mobile_devices():
    """获取已配对设备列表"""
    try:
        server = _get_mobile_server()
        devices = server.token_manager.get_paired_devices()
        return jsonify({'devices': [{'device_name': d['device_name'], 'paired_at': d['paired_at'], 'token': d['token'], 'token_display': d['token'][:8] + '...'} for d in devices]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/revoke', methods=['POST'])
def mobile_revoke():
    """撤销指定设备的令牌"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        server = _get_mobile_server()
        token = data.get('token', '')
        if not token:
            return jsonify({'error': '缺少 token'}), 400
        if not server.token_manager.revoke_token(token):
            return jsonify({'error': '令牌不存在或已撤销'}), 404
        return jsonify({'status': 'revoked'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/revoke-all', methods=['POST'])
def mobile_revoke_all():
    """撤销所有已配对设备的令牌"""
    try:
        server = _get_mobile_server()
        server.token_manager.revoke_all()
        return jsonify({'status': 'revoked_all'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/pending-flutter-uploads', methods=['GET'])
def pending_flutter_uploads():
    """返回 Flutter App 上传的待导入会话列表"""
    with _flutter_upload_lock:
        sessions = list(_flutter_upload_sessions.values())
    return jsonify({'sessions': sessions})


@app.route('/api/mobile/pending-flutter-uploads/clear', methods=['POST'])
def clear_flutter_upload():
    """清除指定的 Flutter App 上传通知（导入开始后调用）"""
    data = request.get_json(force=True, silent=True) or {}
    upload_dir = data.get('upload_dir', '')
    with _flutter_upload_lock:
        _flutter_upload_sessions.pop(upload_dir, None)
    return jsonify({'status': 'cleared'})


# ============================================================================
# 导入 API
# ============================================================================

# 导入管理器
try:
    from .import_manager import get_import_manager, FileConflict
except ImportError:
    from import_manager import get_import_manager, FileConflict

# 导入检查任务（步骤1）状态存储
_import_check_tasks = {}
_import_check_lock = threading.Lock()


def _set_import_check_task(task_id, **kwargs):
    """线程安全更新导入检查任务状态"""
    with _import_check_lock:
        task = _import_check_tasks.get(task_id)
        if not task:
            return
        task.update(kwargs)
        task['updated_at'] = datetime.now().isoformat()


def _perform_import_check(source_path: Path, progress_callback=None):
    """执行导入路径检查，支持进度回调

    性能优化：在扫描时一次性收集 size/mtime/EXIF，避免后续重复调用
    """
    # 统计源目录中的媒体文件（使用 constants 模块）
    MEDIA_FORMATS = _MEDIA_FORMATS


    def emit(progress, stage, detail=''):
        if progress_callback:
            progress_callback(max(0, min(100, int(progress))), stage, detail)

    media_files = []
    total_size = 0

    # 阶段1：扫描源目录并一次性收集所有信息（0% -> 50%）
    emit(0, 'scanning', '开始扫描源目录...')

    # 先统计文件总数（用于进度显示）
    all_files_total = sum(len(files) for _, _, files in os.walk(source_path))
    scanned_files = 0

    # EXIF 读取函数（提前定义，避免重复定义）
    def _get_exif_datetime_fast(path):
        """读取 EXIF 拍摄时间，解析为 datetime 对象（与 media_date 类型一致），
        失败返回 None。返回 datetime 后，预筛 key 用 isoformat() 统一格式。"""
        try:
            from PIL import Image, ExifTags
            with Image.open(path) as img:
                exif_data = img._getexif()
                if not exif_data:
                    return None
                tag_map = {v: k for k, v in ExifTags.TAGS.items()}
                for tag_name in ('DateTimeOriginal', 'DateTime'):
                    tag_id = tag_map.get(tag_name)
                    if tag_id and tag_id in exif_data:
                        value = exif_data[tag_id]
                        if isinstance(value, str):
                            try:
                                from datetime import datetime as _dt
                                return _dt.strptime(value, "%Y:%m:%d %H:%M:%S")
                            except ValueError:
                                return None
        except Exception:
            pass
        return None

    # 单次遍历：收集 size, mtime, exif_datetime
    for root, _, files in os.walk(source_path):
        for filename in files:
            scanned_files += 1
            file_path = Path(root) / filename

            if file_path.suffix.lower() in MEDIA_FORMATS:
                try:
                    stat_info = file_path.stat()
                    file_size = stat_info.st_size
                    file_mtime = stat_info.st_mtime
                except OSError:
                    continue

                # 一次性读取 EXIF（用于后续重复检测预筛）
                exif_datetime = _get_exif_datetime_fast(file_path)

                total_size += file_size
                media_files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_size,
                    'mtime': file_mtime,           # 用于日期分组
                    'exif_datetime': exif_datetime, # 用于重复检测预筛
                    'thumbnail_url': f'/api/album/thumbnail?path={urllib.parse.quote(str(file_path))}'
                })

            if all_files_total > 0:
                stage_progress = int((scanned_files / all_files_total) * 50)
                emit(stage_progress, 'scanning', f'扫描中... {scanned_files}/{all_files_total}')

    # 阶段2：按日期分组（50% -> 55%）—— 使用缓存的 mtime
    emit(50, 'grouping', '按日期整理预览...')
    date_folders = []
    if media_files:
        from collections import defaultdict
        files_by_date = defaultdict(list)
        total_media = len(media_files)
        for idx, file in enumerate(media_files, 1):
            # 使用缓存的 mtime，不再调用 stat()
            mtime = file.get('mtime')
            if mtime:
                date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m')
                files_by_date[date_str].append(file)
            stage_progress = 50 + int((idx / total_media) * 5)
            emit(stage_progress, 'grouping', f'整理日期... {idx}/{total_media}')

        for date_str, files in sorted(files_by_date.items(), reverse=True):
            date_folders.append({
                'name': date_str,
                'count': len(files),
                'size': sum(f['size'] for f in files),
                'files': sorted(files, key=lambda x: x['name'])
            })

    # 计算文件MD5哈希值的函数（使用 utils.compute_md5，统一 1MB chunk）
    calculate_md5 = _compute_md5

    # 阶段3：源重复检测（55% -> 75%）—— 两阶段预筛
    # 阶段3a（55%~62%）：建预筛索引，用 (size, exif_time) 作为轻量特征
    # 阶段3b（62%~75%）：只对特征相同的文件组计算 MD5
    # 性能优化：使用扫描时缓存的 size 和 exif_datetime，不再重复调用 stat/EXIF

    emit(55, 'source_duplicates', '建立源文件预筛索引...')
    source_duplicates = {}
    md5_to_files = {}

    source_prescan = {}  # key: (size, exif_str|None), value: [file_obj]
    total_prescan = len(media_files)
    for idx, file in enumerate(media_files, 1):
        # 使用缓存的 size 和 exif_datetime（datetime 对象，统一用 isoformat 作为 key）
        size = file.get('size')
        exif_dt = file.get('exif_datetime')
        if size is None:
            continue
        exif_str = exif_dt.isoformat() if exif_dt else None
        key = (size, exif_str)
        if key not in source_prescan:
            source_prescan[key] = []
        source_prescan[key].append(file)
        if total_prescan > 0:
            stage_progress = 55 + int((idx / total_prescan) * 7)
            emit(stage_progress, 'source_duplicates', f'建立预筛索引... {idx}/{total_prescan}')

    # 只对特征相同的文件组计算 MD5（可能有重复）
    # 性能优化：并行计算 MD5
    candidate_groups = [files for files in source_prescan.values() if len(files) > 1]
    candidate_files_for_md5 = [file for group in candidate_groups for file in group]
    total_candidate_files = len(candidate_files_for_md5)

    # 并行计算需要的模块和参数（提前准备，避免后续阶段未定义）
    import concurrent.futures
    # os.cpu_count() 在某些受限环境下可能返回 None，需要兜底
    cpu_count = os.cpu_count() or 2
    max_workers = max(1, cpu_count - 1)

    if candidate_files_for_md5:
        def _compute_file_md5(file):
            """计算单个文件的 MD5，返回 (file, md5_hash)"""
            file_path = Path(file['path'])
            md5_hash = calculate_md5(file_path)
            return (file, md5_hash)

        md5_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_compute_file_md5, file): file for file in candidate_files_for_md5}
            for future in concurrent.futures.as_completed(futures):
                md5_computed = len(md5_results) + 1
                if total_candidate_files > 0:
                    stage_progress = 62 + int((md5_computed / total_candidate_files) * 13)
                    emit(stage_progress, 'source_duplicates', f'候选组 MD5 计算... {md5_computed}/{total_candidate_files}')
                try:
                    file, md5_hash = future.result()
                    md5_results.append((file, md5_hash))
                except Exception:
                    pass

        # 汇总 MD5 结果
        for file, md5_hash in md5_results:
            if md5_hash:
                if md5_hash not in md5_to_files:
                    md5_to_files[md5_hash] = []
                md5_to_files[md5_hash].append(file)

    for md5_hash, files in md5_to_files.items():
        if len(files) > 1:
            source_duplicates[md5_hash] = files

    # 阶段4：目标重复检测（75% -> 98%）—— 两阶段去重
    # 阶段4a（75%~82%）：建预筛索引，用 (size, exif_time) 作为轻量特征，不算 MD5
    # 阶段4b（82%~90%）：对预筛候选集计算相册文件 MD5
    # 阶段4c（90%~98%）：遍历源文件，命中预筛才算 MD5，精确比对
    # 性能优化：使用缓存的 size 和 exif_datetime，避免重复调用

    emit(75, 'target_duplicates', '建立预筛索引...')
    target_duplicates = {}
    album_path = get_album_path()

    if album_path:
        album_path = Path(album_path)

        # --- 阶段4a：从数据库构建预筛索引 (size, exif_time) → [file_path] ---
        # 优化：直接查询数据库，避免重新扫描整个相册文件夹
        # 若 DB 为空（相册未被索引过），回退到文件系统扫描，确保不漏检
        prescan_index = {}   # key: (size, exif_str|None), value: [Path]
        target_media_files = []
        try:
            from database import SessionLocal, Photo as PhotoModel
            db = SessionLocal()
            try:
                db_photos = db.query(PhotoModel.path, PhotoModel.size, PhotoModel.media_date, PhotoModel.md5_hash).all()
                for p_path, p_size, p_media_date, p_md5 in db_photos:
                    if p_path and p_size:
                        target_media_files.append((Path(p_path), p_size, p_media_date, p_md5))
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"从数据库加载预筛索引失败，回退到文件系统扫描: {e}")
            target_media_files = []

        # DB 为空时回退到文件系统扫描（相册存在但未被索引）
        # DB 不为空时，若源文件 key 全部命中预筛索引则跳过；否则追加文件系统扫描以补齐
        if not target_media_files:
            logger.info("数据库中无相册记录，回退到文件系统扫描以检测目标重复")
            for file in album_path.rglob('*'):
                if file.is_file() and file.suffix.lower() in MEDIA_FORMATS:
                    try:
                        size = file.stat().st_size
                        exif_dt = _get_exif_datetime_fast(file)
                        target_media_files.append((file, size, exif_dt))
                    except OSError:
                        continue

        total_prescan = len(target_media_files)
        for idx, entry in enumerate(target_media_files, 1):
            # entry: (file, size, media_date) from FS fallback, or (file, size, media_date, md5_hash) from DB
            file, size, media_date = entry[0], entry[1], entry[2]
            md5_hash = entry[3] if len(entry) > 3 else None
            exif_str = media_date.isoformat() if media_date else None
            key = (size, exif_str)
            if key not in prescan_index:
                prescan_index[key] = []
            prescan_index[key].append((file, md5_hash))
            if total_prescan > 0:
                stage_progress = 75 + int((idx / total_prescan) * 7)
                emit(stage_progress, 'target_duplicates', f'建立预筛索引... {idx}/{total_prescan}')

        # --- 阶段4b：收集候选集并计算相册侧 MD5 ---
        # 先用源文件特征查预筛索引，找出可能重复的相册文件候选集
        # 性能优化：使用缓存的 size 和 exif_datetime（统一用 isoformat 作为 key）
        source_keys = set()
        for file in media_files:
            size = file.get('size')
            exif_dt = file.get('exif_datetime')
            if size is not None:
                exif_str = exif_dt.isoformat() if exif_dt else None
                source_keys.add((size, exif_str))

        # 兜底：若存在未命中的源 key（DB 中没有对应记录，可能相册未被索引），
        # 追加一次文件系统扫描补齐预筛索引，确保不漏检已在相册中但未入库的文件
        missing_keys = {k for k in source_keys if k not in prescan_index}
        if missing_keys:
            logger.info(f"DB 预筛索引有 {len(missing_keys)} 个源 key 缺失，追加文件系统扫描补齐")
            for file in album_path.rglob('*'):
                if file.is_file() and file.suffix.lower() in MEDIA_FORMATS:
                    try:
                        size = file.stat().st_size
                        exif_dt = _get_exif_datetime_fast(file)
                        exif_str = exif_dt.isoformat() if exif_dt else None
                        key = (size, exif_str)
                        if key in missing_keys and key not in prescan_index:
                            prescan_index[key] = [(file, None)]
                    except OSError:
                        continue

        # 只对与源文件特征匹配的相册文件计算 MD5
        # 优先使用数据库缓存的 md5_hash，缺失时才执行 I/O 计算
        candidate_target_files = []
        for key in source_keys:
            if key in prescan_index:
                candidate_target_files.extend(prescan_index[key])

        target_md5_to_files = {}
        total_candidates = len(candidate_target_files)

        if candidate_target_files:
            def _compute_target_md5(file_and_md5):
                """计算相册文件的 MD5，优先使用数据库缓存

                file_and_md5: (Path, str|None) — 文件路径和缓存的 md5_hash
                """
                file, cached_md5 = file_and_md5
                if cached_md5:
                    md5_hash = cached_md5
                else:
                    md5_hash = calculate_md5(file)
                try:
                    file_size = file.stat().st_size
                except OSError:
                    file_size = 0
                return (file, md5_hash, file_size)

            md5_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_compute_target_md5, entry): entry for entry in candidate_target_files}
                for future in concurrent.futures.as_completed(futures):
                    md5_computed = len(md5_results) + 1
                    if total_candidates > 0:
                        stage_progress = 82 + int((md5_computed / total_candidates) * 8)
                        emit(stage_progress, 'target_duplicates', f'候选集 MD5 计算... {md5_computed}/{total_candidates}')
                    try:
                        file, md5_hash, file_size = future.result()
                        md5_results.append((file, md5_hash, file_size))
                    except Exception:
                        pass

            # 汇总结果
            for file, md5_hash, file_size in md5_results:
                if md5_hash:
                    file_obj = {
                        'name': file.name,
                        'path': str(file),
                        'size': file_size,
                        'thumbnail_url': f'/api/album/thumbnail?path={urllib.parse.quote(str(file))}'
                    }
                    if md5_hash not in target_md5_to_files:
                        target_md5_to_files[md5_hash] = []
                    target_md5_to_files[md5_hash].append(file_obj)
        else:
            emit(90, 'target_duplicates', '候选集为空，跳过 MD5 计算')

        # --- 阶段4c：遍历源文件，命中候选集才算 MD5 比对 ---
        # 性能优化：并行计算 MD5，使用缓存的 size 和 exif_datetime（统一 isoformat key）
        compare_targets = media_files
        # 筛选出需要计算 MD5 的文件
        files_needing_md5 = []
        for file in compare_targets:
            size = file.get('size')
            exif_dt = file.get('exif_datetime')
            if size is None:
                continue
            exif_str = exif_dt.isoformat() if exif_dt else None
            key = (size, exif_str)
            if key in prescan_index:
                files_needing_md5.append(file)

        total_compare = len(files_needing_md5)
        md5_compare_results = []

        if files_needing_md5:
            def _compare_source_md5(file):
                """计算源文件 MD5 用于比对"""
                file_path = Path(file['path'])
                md5_hash = calculate_md5(file_path)
                return (file, md5_hash)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_compare_source_md5, file): file for file in files_needing_md5}
                for future in concurrent.futures.as_completed(futures):
                    md5_computed = len(md5_compare_results) + 1
                    if total_compare > 0:
                        stage_progress = 90 + int((md5_computed / total_compare) * 8)
                        emit(stage_progress, 'target_duplicates', f'目标重复检测... {md5_computed}/{total_compare}')
                    try:
                        file, md5_hash = future.result()
                        md5_compare_results.append((file, md5_hash))
                    except Exception:
                        pass

        # 汇总比对结果
        for file, md5_hash in md5_compare_results:
            if md5_hash and md5_hash in target_md5_to_files:
                if md5_hash not in target_duplicates:
                    target_duplicates[md5_hash] = target_md5_to_files[md5_hash] + [file]
                else:
                    target_duplicates[md5_hash].append(file)

    emit(100, 'completed', '检查完成')

    return {
        'status': 'valid',
        'source_path': str(source_path),
        'media_count': len(media_files),
        'total_size': total_size,
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'preview': sorted(media_files, key=lambda x: x['name'])[:5],
        'date_folders': date_folders,
        'target_duplicates': target_duplicates,
        'source_duplicates': source_duplicates,
        'skipped_files': 0
    }

@app.route('/api/import/check', methods=['POST'])
def check_import_path():
    """检查导入路径是否有效（同步接口，兼容保留）"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        source_path = data.get('source_path')
        
        if not source_path:
            return jsonify({'error': '缺少 source_path 参数'}), 400
        
        source_path = Path(source_path)
        if not source_path.exists():
            return jsonify({'error': f'源路径不存在: {source_path}'}), 404
        
        if not source_path.is_dir():
            return jsonify({'error': f'源路径不是目录: {source_path}'}), 400
        
        result = _perform_import_check(source_path)
        return jsonify(result)
    except Exception as e:
        logger.error(f"API 错误 POST /api/import/check: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/check/start', methods=['POST'])
def start_import_check():
    """启动导入路径检查（异步，带真实进度）"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        source_path = data.get('source_path')

        if not source_path:
            return jsonify({'error': '缺少 source_path 参数'}), 400

        source_path_obj = Path(source_path)
        if not source_path_obj.exists():
            return jsonify({'error': f'源路径不存在: {source_path_obj}'}), 404
        if not source_path_obj.is_dir():
            return jsonify({'error': f'源路径不是目录: {source_path_obj}'}), 400

        check_id = f"check_{uuid.uuid4().hex[:12]}"
        with _import_check_lock:
            _import_check_tasks[check_id] = {
                'check_id': check_id,
                'status': 'running',
                'progress': 0,
                'stage': 'queued',
                'detail': '任务已创建',
                'result': None,
                'error': None,
                'started_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

        def worker():
            def _ttl_cleanup():
                with _import_check_lock:
                    _import_check_tasks.pop(check_id, None)
                logger.debug(f"[import_check] 任务 {check_id} TTL 已清理")

            try:
                def progress_cb(progress, stage, detail):
                    _set_import_check_task(
                        check_id,
                        progress=progress,
                        stage=stage,
                        detail=detail
                    )

                result = _perform_import_check(source_path_obj, progress_cb)
                _set_import_check_task(
                    check_id,
                    status='completed',
                    progress=100,
                    stage='completed',
                    detail='检查完成',
                    result=result
                )
            except Exception as e:
                logger.error(f"导入检查任务失败 {check_id}: {e}", exc_info=True)
                _set_import_check_task(
                    check_id,
                    status='failed',
                    stage='failed',
                    detail='检查失败',
                    error=str(e)
                )
            finally:
                # 5 分钟后自动清理任务条目，防止内存泄漏
                t_cleanup = threading.Timer(300, _ttl_cleanup)
                t_cleanup.daemon = True
                t_cleanup.start()

        threading.Thread(target=worker, daemon=True).start()
        return jsonify({'status': 'started', 'check_id': check_id})
    except Exception as e:
        logger.error(f"API 错误 POST /api/import/check/start: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/import/check/progress/<check_id>', methods=['GET'])
def get_import_check_progress(check_id):
    """获取导入路径检查进度"""
    with _import_check_lock:
        task = _import_check_tasks.get(check_id)

    if not task:
        return jsonify({'error': '检查任务不存在'}), 404

    payload = {
        'check_id': task['check_id'],
        'status': task['status'],
        'progress': task['progress'],
        'stage': task['stage'],
        'detail': task['detail'],
        'error': task['error']
    }
    if task['status'] == 'completed' and task['result'] is not None:
        payload['result'] = task['result']

    return jsonify(payload)

@app.route('/api/import/start', methods=['POST'])
def start_import():
    """开始导入"""
    try:
        data = request.get_json(force=True, silent=True) or {}
        source_path = data.get('source_path')
        target_path = data.get('target_path')
        import_mode = data.get('import_mode', 'copy')

        # 合法性校验：只接受 'copy' 或 'move'，其他值回落到 'copy'
        if import_mode not in ('copy', 'move'):
            import_mode = 'copy'

        # target_path 缺省时回退到配置的相册路径
        if not target_path:
            target_path = get_album_path()

        if not source_path or not target_path:
            return jsonify({'error': '缺少必需参数'}), 400
        
        source_path = Path(source_path)
        target_path = Path(target_path)
        
        if not source_path.exists() or not source_path.is_dir():
            return jsonify({'error': f'源路径无效: {source_path}'}), 400
        
        if not target_path.exists() or not target_path.is_dir():
            return jsonify({'error': f'目标路径无效: {target_path}'}), 400
        
        # 生成导入 ID
        import_id = f"import_{int(datetime.now().timestamp() * 1000)}"
        
        # 创建导入任务
        import_manager = get_import_manager()
        import_manager.create_import(import_id, str(source_path), str(target_path))
        
        # 后台启动导入
        import_manager.start_import_async(import_id, str(source_path), str(target_path), import_mode)
        
        logger.info(f"导入已启动: {import_id}，模式: {import_mode}")
        
        return jsonify({
            'status': 'started',
            'import_id': import_id,
            'message': '导入已开始'
        })
    except Exception as e:
        logger.error(f"API 错误 POST /api/import/start: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/progress/<import_id>', methods=['GET'])
def get_import_progress(import_id):
    """获取导入进度"""
    try:
        import_manager = get_import_manager()
        progress_dict = import_manager.get_progress_dict(import_id)
        
        if not progress_dict:
            return jsonify({'error': '导入任务不存在'}), 404
        
        return jsonify(progress_dict)
    except Exception as e:
        logger.error(f"API 错误 GET /api/import/progress: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/cancel/<import_id>', methods=['POST'])
def cancel_import(import_id):
    """取消导入"""
    try:
        import_manager = get_import_manager()
        progress = import_manager.get_progress(import_id)
        
        if not progress:
            return jsonify({'error': '导入任务不存在'}), 404
        
        import_manager.cancel_import(import_id)
        
        logger.info(f"导入已取消: {import_id}")
        
        return jsonify({
            'status': 'cancelled',
            'import_id': import_id,
            'message': '导入已取消'
        })
    except Exception as e:
        logger.error(f"API 错误 POST /api/import/cancel: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/pause/<import_id>', methods=['POST'])
def pause_import(import_id):
    """暂停导入"""
    try:
        import_manager = get_import_manager()
        progress = import_manager.get_progress(import_id)
        
        if not progress:
            return jsonify({'error': '导入任务不存在'}), 404
        
        import_manager.pause_import(import_id)
        
        logger.info(f"导入已暂停: {import_id}")
        
        return jsonify({
            'status': 'paused',
            'import_id': import_id,
            'message': '导入已暂停'
        })
    except Exception as e:
        logger.error(f"API 错误 POST /api/import/pause: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/resume/<import_id>', methods=['POST'])
def resume_import(import_id):
    """继续导入"""
    try:
        import_manager = get_import_manager()
        progress = import_manager.get_progress(import_id)
        
        if not progress:
            return jsonify({'error': '导入任务不存在'}), 404
        
        import_manager.resume_import(import_id)
        
        logger.info(f"导入已继续: {import_id}")
        
        return jsonify({
            'status': 'processing',
            'import_id': import_id,
            'message': '导入已继续'
        })
    except Exception as e:
        logger.error(f"API 错误 POST /api/import/resume: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/delete', methods=['POST'])
def delete_files():
    """删除指定的文件列表（支持删除相册内照片或源文件夹中的文件，并同步清除 MD5 记录）"""
    try:
        data = request.get_json()
        if not data or 'paths' not in data:
            return jsonify({'error': '请提供要删除的文件路径列表'}), 400
        
        file_paths = data.get('paths', [])
        if not isinstance(file_paths, list):
            return jsonify({'error': 'paths 必须是数组'}), 400
        
        if len(file_paths) == 0:
            return jsonify({'error': '没有要删除的文件'}), 400
        
        config_manager = get_config_manager()
        album_path = config_manager.get_album_path() or ''
        album_root = Path(album_path).resolve() if album_path else None
        
        # 可选：允许删除的源文件夹路径（用于导入时的重复文件清理）
        allowed_source_paths = data.get('source_paths', [])
        if isinstance(allowed_source_paths, str):
            allowed_source_paths = [allowed_source_paths]
        allowed_source_roots = [Path(p).resolve() for p in allowed_source_paths if p]

        deleted = []
        failed = []
        deleted_resolved_paths = []  # 记录成功删除文件的 resolved path，用于批量清理 MD5 记录

        for file_path in file_paths:
            try:
                path = Path(file_path)
                path_resolved = path.resolve()

                # 安全检查：文件必须在允许的目录内（相册目录或指定的源文件夹）
                is_allowed = False
                
                # 检查是否在相册目录内
                if album_root:
                    try:
                        path_resolved.relative_to(album_root)
                        is_allowed = True
                    except ValueError:
                        pass
                
                # 检查是否在允许的源文件夹内
                if not is_allowed and allowed_source_roots:
                    for source_root in allowed_source_roots:
                        try:
                            path_resolved.relative_to(source_root)
                            is_allowed = True
                            break
                        except ValueError:
                            pass
                
                if not is_allowed:
                    logger.warning(f"拒绝删除允许目录外的文件: {file_path}")
                    failed.append({'path': file_path, 'error': '访问被拒绝：文件不在允许删除的目录内'})
                    continue

                # 安全检查：不能删除相册根目录或源文件夹根目录本身
                if album_root and path_resolved == album_root:
                    logger.warning(f"禁止删除相册根目录: {file_path}")
                    failed.append({'path': file_path, 'error': '禁止删除相册根目录'})
                    continue
                
                skip_outer = False
                for source_root in allowed_source_roots:
                    if path_resolved == source_root:
                        logger.warning(f"禁止删除源文件夹根目录: {file_path}")
                        failed.append({'path': file_path, 'error': '禁止删除源文件夹根目录'})
                        skip_outer = True
                        break
                if skip_outer:
                    continue

                # 确保目标是文件而非目录
                if path.is_dir():
                    failed.append({'path': file_path, 'error': '目标是目录，不允许删除目录'})
                    continue

                # 确保文件存在
                if not path.exists():
                    logger.warning(f"文件不存在: {file_path}")
                    failed.append({'path': file_path, 'error': '文件不存在'})
                    continue

                # 删除文件
                path.unlink()
                deleted.append(file_path)
                deleted_resolved_paths.append(path_resolved)
                logger.info(f"已删除文件: {file_path}")

            except Exception as e:
                logger.error(f"删除文件失败 {file_path}: {e}")
                failed.append({'path': file_path, 'error': str(e)})
        
        # 批量清除 MD5 记录（只读取一次 JSON，批量修改，只写回一次）
        if album_root and deleted_resolved_paths:
            records_file = album_root / '.photo_organizer.json'
            if records_file.exists():
                try:
                    import json as _json
                    with open(records_file, 'r', encoding='utf-8') as f:
                        raw = _json.load(f)
                    # _save_target_records 写入的是 {version, records: {md5: path}, ...}
                    # 需先取 records 子字段；旧格式（扁平 dict）直接是 {md5: path}
                    records = raw.get('records', raw) if isinstance(raw, dict) else {}
                    
                    # 构建已删除文件的 resolved path 集合，用于快速匹配
                    deleted_paths_set = set(str(p) for p in deleted_resolved_paths)
                    
                    # 批量清除匹配的记录
                    to_remove = [
                        k for k, v in records.items() 
                        if isinstance(v, str) and str(Path(v).resolve()) in deleted_paths_set
                    ]
                    
                    if to_remove:
                        for k in to_remove:
                            del records[k]
                        # 保持原始格式写回（嵌套 or 扁平）
                        if 'records' in raw:
                            raw['records'] = records
                            out_data = raw
                        else:
                            out_data = records
                        with open(records_file, 'w', encoding='utf-8') as f:
                            _json.dump(out_data, f, ensure_ascii=False, indent=2)
                        logger.info(f"已从 MD5 记录中批量移除 {len(to_remove)} 条（共删除 {len(deleted)} 个文件）")
                except Exception as e_rec:
                    logger.warning(f"批量清除 MD5 记录失败: {e_rec}")
        
        return jsonify({
            'status': 'completed',
            'deleted_count': len(deleted),
            'failed_count': len(failed),
            'deleted': deleted,
            'failed': failed
        })
    except Exception as e:
        logger.error(f"API 错误 POST /api/files/delete: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# 错误处理
# ============================================================================

# ============================================================================
# 前端文件服务（重要：PyWebView 需要通过 Flask 获取前端）
# 支持 Vite 构建的 React 前端
# ============================================================================

# MIME 类型映射
MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.ttf': 'font/ttf',
    '.eot': 'application/vnd.ms-fontobject',
}

def get_mime_type(filename):
    """根据文件扩展名获取 MIME 类型"""
    ext = Path(filename).suffix.lower()
    return MIME_TYPES.get(ext, 'application/octet-stream')

@app.route('/')
def index():
    """提供主页面 - 支持 Vite 构建的前端"""
    try:
        # 优先使用 Vite 构建产物
        frontend_dir = Path(__file__).parent.parent / 'frontend'
        dist_index = frontend_dir / 'dist' / 'index.html'

        if dist_index.exists():
            # 使用 Vite 构建产物
            with open(dist_index, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}

        # 回退到旧前端
        index_file = frontend_dir / 'index.html'
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}

        logger.error(f"找不到 index.html")
        return jsonify({'error': '找不到 index.html'}), 404
    except Exception as e:
        logger.error(f"加载 index.html 失败: {e}")
        return jsonify({'error': '加载页面失败'}), 500

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """提供 Vite 构建的静态资源文件"""
    try:
        # 安全检查：防止路径遍历
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            logger.warning(f"非法路径访问尝试: {filename}")
            return jsonify({'error': '访问被拒绝'}), 403

        frontend_dir = Path(__file__).parent.parent / 'frontend'
        file_path = frontend_dir / 'dist' / 'assets' / filename

        # 确保文件在 dist/assets 目录内
        try:
            file_path.resolve().relative_to((frontend_dir / 'dist' / 'assets').resolve())
        except ValueError:
            logger.warning(f"路径遍历攻击尝试: {filename}")
            return jsonify({'error': '访问被拒绝'}), 403

        if not file_path.exists():
            logger.warning(f"资源文件不存在: {filename}")
            return jsonify({'error': f'找不到文件: {filename}'}), 404

        # 根据扩展名确定 MIME 类型
        mime_type = get_mime_type(filename)

        with open(file_path, 'rb') as f:
            return f.read(), 200, {'Content-Type': mime_type}
    except Exception as e:
        logger.error(f"加载资源文件失败: {filename}, 错误: {e}")
        return jsonify({'error': '加载资源文件失败'}), 500

@app.route('/favicon.svg')
def favicon_svg():
    """网站图标 SVG"""
    try:
        frontend_dir = Path(__file__).parent.parent / 'frontend'
        favicon_file = frontend_dir / 'dist' / 'favicon.svg'

        if not favicon_file.exists():
            favicon_file = frontend_dir / 'public' / 'favicon.svg'

        if favicon_file.exists():
            with open(favicon_file, 'rb') as f:
                return f.read(), 200, {'Content-Type': 'image/svg+xml'}

        return '', 204
    except Exception as e:
        return '', 204

@app.route('/favicon.ico')
def favicon():
    """网站图标"""
    return favicon_svg()

# 保留旧前端路由作为回退（开发时可能需要）
@app.route('/js/<path:filename>')
def serve_js(filename):
    """提供 JavaScript 文件（旧前端回退）"""
    try:
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': '访问被拒绝'}), 403

        frontend_dir = Path(__file__).parent.parent / 'frontend-legacy'
        file_path = frontend_dir / 'js' / filename

        if not file_path.exists():
            return jsonify({'error': f'找不到文件: {filename}'}), 404

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'application/javascript; charset=utf-8'}
    except Exception as e:
        return jsonify({'error': '加载 JS 文件失败'}), 500

@app.route('/css/<path:filename>')
def serve_css(filename):
    """提供 CSS 文件（旧前端回退）"""
    try:
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': '访问被拒绝'}), 403

        frontend_dir = Path(__file__).parent.parent / 'frontend-legacy'
        file_path = frontend_dir / 'css' / filename

        if not file_path.exists():
            return jsonify({'error': f'找不到文件: {filename}'}), 404

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/css; charset=utf-8'}
    except Exception as e:
        return jsonify({'error': '加载 CSS 文件失败'}), 500

@app.route('/frontend/modules/<path:filename>')
def serve_frontend_modules(filename):
    """提供前端模块化架构的 JavaScript 模块文件"""
    try:
        # 安全检查：防止路径遍历
        if '..' in filename or filename.startswith('/'):
            logger.warning(f"非法路径访问尝试: {filename}")
            return jsonify({'error': '访问被拒绝'}), 403
        
        frontend_dir = Path(__file__).parent.parent / 'frontend'
        file_path = frontend_dir / 'modules' / filename
        
        # 确保文件在 frontend/modules 目录内
        try:
            file_path.resolve().relative_to(frontend_dir.resolve())
        except ValueError:
            logger.warning(f"路径遍历攻击尝试: {filename}")
            return jsonify({'error': '访问被拒绝'}), 403
        
        if not file_path.exists():
            logger.warning(f"模块化文件不存在: {filename}")
            return jsonify({'error': f'找不到文件: {filename}'}), 404
        
        # 根据文件扩展名设置正确的 MIME 类型
        ext = file_path.suffix.lower()
        if ext == '.js':
            content_type = 'application/javascript; charset=utf-8'
        elif ext == '.css':
            content_type = 'text/css; charset=utf-8'
        else:
            content_type = 'application/octet-stream'
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': content_type}
    except Exception as e:
        logger.error(f"加载前端模块化文件失败: {filename}, 错误: {e}")
        return jsonify({'error': '加载模块化文件失败'}), 500

@app.route('/diagnostic')
def diagnostic():
    """诊断工具页面"""
    try:
        frontend_dir = Path(__file__).parent.parent / 'frontend'
        diagnostic_file = frontend_dir / 'diagnostic.html'
        
        if not diagnostic_file.exists():
            return jsonify({'error': '找不到诊断工具'}), 404
        
        with open(diagnostic_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"加载诊断工具失败: {e}")
        return jsonify({'error': '加载诊断工具失败'}), 500

@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return jsonify({'error': '404 Not Found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return jsonify({'error': '500 Internal Server Error'}), 500


# ============================================================================
# 缓存管理 API
# ============================================================================

@app.route('/api/cache/cleanup', methods=['POST'])
def cache_cleanup():
    """清理缩略图缓存（按大小限制，LRU 淘汰策略）

    请求体（JSON，可选）：
      max_size_mb: float  — 允许保留的最大缓存大小（MB），默认 500

    响应：
      deleted_count: int  — 删除的文件数
      freed_mb: float     — 释放的空间（MB）
      remaining_mb: float — 清理后剩余大小（MB）
    """
    try:
        data = request.get_json(silent=True) or {}
        max_size_mb = float(data.get('max_size_mb', 500))
        if max_size_mb <= 0:
            return jsonify({'error': 'max_size_mb 必须大于 0'}), 400

        tm = get_thumbnail_manager()
        result = tm.cleanup_cache_by_size(max_size_mb=max_size_mb)
        return jsonify(result)
    except Exception as e:
        logger.error(f"API 错误 POST /api/cache/cleanup: {e}")
        return jsonify({'error': str(e)}), 500



# ============================================================================
# 配对模式管理 API（桥接移动接入服务）
# ============================================================================

@app.route('/api/mobile/pairing/start', methods=['POST'])
def mobile_pairing_start():
    """开启配对模式（启动 mDNS 广播）"""
    try:
        server = _get_mobile_server()
        if server is None:
            return jsonify({'error': '移动接入服务未启动'}), 400
        result = server.start_pairing_mode()
        return jsonify(result)
    except Exception as e:
        logger.error(f'[API] 开启配对模式失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/pairing/stop', methods=['POST'])
def mobile_pairing_stop():
    """停止配对模式"""
    try:
        server = _get_mobile_server()
        if server:
            server.stop_pairing_mode()
        return jsonify({'status': 'stopped'})
    except Exception as e:
        logger.error(f'[API] 停止配对模式失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/pairing/pending', methods=['GET'])
def mobile_pairing_pending():
    """PC 端轮询待确认配对请求"""
    try:
        server = _get_mobile_server()
        if server is None:
            return jsonify({'status': 'none'})
        pending = server._pairing.get_pending()
        if pending is None:
            return jsonify({'status': 'none'})
        return jsonify({
            'status': 'pending',
            'device_name': pending.device_name,
            'requested_at': pending.requested_at,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/pairing/confirm', methods=['POST'])
def mobile_pairing_confirm():
    """PC 端确认配对 → 返回配对码"""
    try:
        server = _get_mobile_server()
        if server is None:
            return jsonify({'error': '移动接入服务未启动'}), 400
        code = server._pairing.confirm_pending()
        return jsonify({
            'status': 'confirmed',
            'pairing_code': code,
            'expires_in': 120,
        })
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/pairing/reject', methods=['POST'])
def mobile_pairing_reject():
    """PC 端拒绝配对"""
    try:
        server = _get_mobile_server()
        if server:
            server._pairing.reject_pending()
        return jsonify({'status': 'rejected'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/pairing/cancel', methods=['POST'])
def mobile_pairing_cancel():
    """PC 端取消配对请求（桥接至移动接入服务）"""
    try:
        server = _get_mobile_server()
        if server:
            server._pairing.clear_pending()
        return jsonify({'status': 'cancelled'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # 启动 Flask 开发服务器
    logger.info("启动 Flask API 服务器...")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False,  # 禁用重新加载器，避免 PyWebView 中的问题
        threaded=True         # 提升并发处理能力
    )
