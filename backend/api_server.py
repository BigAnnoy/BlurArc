"""
Flask API 服务器 - 相册管理应用的 REST API 接口

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
import os
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
CORS(app)  # 允许跨域请求

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
    
    # 使用数据库统计（如果可用），否则使用文件系统统计
    final_total_files = db_total_files if db_total_files is not None else total_files
    final_video_count = db_video_count if db_video_count is not None else video_count
    final_total_size = db_total_size if db_total_size is not None else total_size
    
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
    """获取指定路径下的照片列表"""
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': '缺少 path 参数'}), 400
        
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
        
        photos = []
        for file in sorted(target_path.iterdir()):
            if file.is_file() and file.suffix.lower() in MEDIA_FORMATS:
                stat = file.stat()
                encoded_path = urllib.parse.quote(str(file))
                file_type = 'photo' if file.suffix.lower() in _IMAGE_FORMATS else 'video'
                photos.append({
                    'name': file.name,
                    'path': str(file),
                    'size': stat.st_size,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'type': file_type,
                    'thumbnail_url': f'/api/album/thumbnail?path={encoded_path}',
                    'url': f'/api/album/file?path={encoded_path}',
                    # preview_url: 视频用 file 路由，图片用专用 preview 路由（支持 HEIC 等格式转换）
                    'preview_url': f'/api/album/file?path={encoded_path}' if file_type == 'video' else f'/api/album/preview?path={encoded_path}',
                })
        
        return jsonify({
            'path': str(target_path),
            'count': len(photos),
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


@app.route('/api/test', methods=['GET'])
def test_api():
    """测试 API"""
    return jsonify({
        'message': 'API 工作正常',
        'timestamp': datetime.now().isoformat()
    })

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
        """读取 EXIF 拍摄时间，失败返回 None"""
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
                        return str(exif_data[tag_id])
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
        # 使用缓存的 size 和 exif_datetime
        size = file.get('size')
        exif_str = file.get('exif_datetime')
        if size is None:
            continue
        key = (size, exif_str)
        if key not in source_prescan:
            source_prescan[key] = []
        source_prescan[key].append(file)
        if total_prescan > 0:
            stage_progress = 55 + int((idx / total_prescan) * 7)
            emit(stage_progress, 'source_duplicates', f'建立预筛索引... {idx}/{total_prescan}')

    # 只对特征相同的文件组计算 MD5（可能有重复）
    candidate_groups = [files for files in source_prescan.values() if len(files) > 1]
    total_candidate_files = sum(len(files) for files in candidate_groups)
    md5_computed = 0

    for group in candidate_groups:
        for file in group:
            file_path = Path(file['path'])
            md5_hash = calculate_md5(file_path)
            if md5_hash:
                if md5_hash not in md5_to_files:
                    md5_to_files[md5_hash] = []
                md5_to_files[md5_hash].append(file)
            md5_computed += 1
            if total_candidate_files > 0:
                stage_progress = 62 + int((md5_computed / total_candidate_files) * 13)
                emit(stage_progress, 'source_duplicates', f'候选组 MD5 计算... {md5_computed}/{total_candidate_files}')

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

        # --- 阶段4a：建预筛索引 (size, exif_time) → [file_path] ---
        prescan_index = {}   # key: (size, exif_str|None), value: [Path]
        target_media_files = []
        for file in album_path.rglob('*'):
            if file.is_file() and file.suffix.lower() in MEDIA_FORMATS:
                target_media_files.append(file)

        total_prescan = len(target_media_files)
        for idx, file in enumerate(target_media_files, 1):
            try:
                size = file.stat().st_size
            except OSError:
                continue
            exif_str = _get_exif_datetime_fast(file)
            key = (size, exif_str)
            if key not in prescan_index:
                prescan_index[key] = []
            prescan_index[key].append(file)
            if total_prescan > 0:
                stage_progress = 75 + int((idx / total_prescan) * 7)
                emit(stage_progress, 'target_duplicates', f'建立预筛索引... {idx}/{total_prescan}')

        # --- 阶段4b：收集候选集并计算相册侧 MD5 ---
        # 先用源文件特征查预筛索引，找出可能重复的相册文件候选集
        # 性能优化：使用缓存的 size 和 exif_datetime
        source_keys = set()
        for file in media_files:
            size = file.get('size')
            exif_str = file.get('exif_datetime')
            if size is not None:
                source_keys.add((size, exif_str))

        # 只对与源文件特征匹配的相册文件计算 MD5
        candidate_target_files = []
        for key in source_keys:
            if key in prescan_index:
                candidate_target_files.extend(prescan_index[key])

        target_md5_to_files = {}
        total_candidates = len(candidate_target_files)
        for idx, file in enumerate(candidate_target_files, 1):
            md5_hash = calculate_md5(file)
            if md5_hash:
                try:
                    file_size = file.stat().st_size
                except OSError:
                    file_size = 0
                file_obj = {
                    'name': file.name,
                    'path': str(file),
                    'size': file_size,
                    'thumbnail_url': f'/api/album/thumbnail?path={urllib.parse.quote(str(file))}'
                }
                if md5_hash not in target_md5_to_files:
                    target_md5_to_files[md5_hash] = []
                target_md5_to_files[md5_hash].append(file_obj)
            if total_candidates > 0:
                stage_progress = 82 + int((idx / total_candidates) * 8)
                emit(stage_progress, 'target_duplicates', f'候选集 MD5 计算... {idx}/{total_candidates}')
            else:
                emit(90, 'target_duplicates', '候选集为空，跳过 MD5 计算')

        # --- 阶段4c：遍历源文件，命中候选集才算 MD5 比对 ---
        # 性能优化：使用缓存的 size 和 exif_datetime
        compare_targets = media_files
        total_compare = len(compare_targets)
        for idx, file in enumerate(compare_targets, 1):
            # 使用缓存的 size 和 exif_datetime
            size = file.get('size')
            exif_str = file.get('exif_datetime')
            if size is None:
                continue
            key = (size, exif_str)
            if key in prescan_index:
                # 命中预筛，才算 MD5
                file_path = Path(file['path'])
                md5_hash = calculate_md5(file_path)
                if md5_hash and md5_hash in target_md5_to_files:
                    if md5_hash not in target_duplicates:
                        target_duplicates[md5_hash] = target_md5_to_files[md5_hash] + [file]
                    else:
                        target_duplicates[md5_hash].append(file)
            if total_compare > 0:
                stage_progress = 90 + int((idx / total_compare) * 8)
                emit(stage_progress, 'target_duplicates', f'目标重复检测... {idx}/{total_compare}')

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
        skip_source_duplicates = data.get('skip_source_duplicates', False)
        skip_target_duplicates = data.get('skip_target_duplicates', False)
        
        # 合法性校验：只接受 'copy' 或 'move'，其他值回落到 'copy'
        if import_mode not in ('copy', 'move'):
            import_mode = 'copy'
        
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
        import_manager.start_import_async(import_id, str(source_path), str(target_path), import_mode, skip_source_duplicates, skip_target_duplicates)
        
        logger.info(f"导入已启动: {import_id}，模式: {import_mode}，跳过源重复: {skip_source_duplicates}，跳过目标重复: {skip_target_duplicates}")
        
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
# ============================================================================

@app.route('/')
def index():
    """提供主页面"""
    try:
        frontend_dir = Path(__file__).parent.parent / 'frontend'
        index_file = frontend_dir / 'index.html'
        
        if not index_file.exists():
            logger.error(f"找不到 index.html: {index_file}")
            return jsonify({'error': '找不到 index.html'}), 404
        
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 修复：返回正确的 MIME 类型
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        logger.error(f"加载 index.html 失败: {e}")
        return jsonify({'error': '加载页面失败'}), 500

@app.route('/js/<path:filename>')
def serve_js(filename):
    """提供 JavaScript 文件"""
    try:
        # 安全检查：防止路径遍历
        if '..' in filename or filename.startswith('/'):
            logger.warning(f"非法路径访问尝试: {filename}")
            return jsonify({'error': '访问被拒绝'}), 403
        
        frontend_dir = Path(__file__).parent.parent / 'frontend'
        file_path = frontend_dir / 'js' / filename
        
        # 确保文件在 frontend/js 目录内
        try:
            file_path.resolve().relative_to(frontend_dir.resolve())
        except ValueError:
            logger.warning(f"路径遍历攻击尝试: {filename}")
            return jsonify({'error': '访问被拒绝'}), 403
        
        if not file_path.exists():
            logger.warning(f"JS 文件不存在: {filename}")
            return jsonify({'error': f'找不到文件: {filename}'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'application/javascript; charset=utf-8'}
    except Exception as e:
        logger.error(f"加载 JS 文件失败: {filename}, 错误: {e}")
        return jsonify({'error': '加载 JS 文件失败'}), 500

@app.route('/css/<path:filename>')
def serve_css(filename):
    """提供 CSS 文件"""
    try:
        # 安全检查：防止路径遍历
        if '..' in filename or filename.startswith('/'):
            logger.warning(f"非法路径访问尝试: {filename}")
            return jsonify({'error': '访问被拒绝'}), 403
        
        frontend_dir = Path(__file__).parent.parent / 'frontend'
        file_path = frontend_dir / 'css' / filename
        
        # 确保文件在 frontend/css 目录内
        try:
            file_path.resolve().relative_to(frontend_dir.resolve())
        except ValueError:
            logger.warning(f"路径遍历攻击尝试: {filename}")
            return jsonify({'error': '访问被拒绝'}), 403
        
        if not file_path.exists():
            logger.warning(f"CSS 文件不存在: {filename}")
            return jsonify({'error': f'找不到文件: {filename}'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/css; charset=utf-8'}
    except Exception as e:
        logger.error(f"加载 CSS 文件失败: {filename}, 错误: {e}")
        return jsonify({'error': '加载 CSS 文件失败'}), 500

@app.route('/favicon.ico')
def favicon():
    """网站图标"""
    try:
        frontend_dir = Path(__file__).parent.parent / 'frontend'
        favicon_file = frontend_dir / 'favicon.svg'
        
        if favicon_file.exists():
            with open(favicon_file, 'rb') as f:
                return f.read(), 200, {'Content-Type': 'image/svg+xml'}
        
        return '', 204
    except Exception as e:
        return '', 204

@app.route('/<filename>.svg')
def serve_svg(filename):
    """提供前端根目录 SVG 文件（如 app-logo.svg）"""
    try:
        # 安全检查：只允许纯文件名，不允许路径穿越
        if '/' in filename or '\\' in filename or '..' in filename:
            return jsonify({'error': '访问被拒绝'}), 403

        frontend_dir = Path(__file__).parent.parent / 'frontend'
        svg_file = frontend_dir / f'{filename}.svg'

        # 确保文件在 frontend 目录内
        try:
            svg_file.resolve().relative_to(frontend_dir.resolve())
        except ValueError:
            return jsonify({'error': '访问被拒绝'}), 403

        if not svg_file.exists():
            return jsonify({'error': f'找不到文件: {filename}.svg'}), 404

        with open(svg_file, 'rb') as f:
            return f.read(), 200, {'Content-Type': 'image/svg+xml; charset=utf-8'}
    except Exception as e:
        logger.error(f"加载 SVG 文件失败: {filename}.svg, 错误: {e}")
        return jsonify({'error': '加载 SVG 文件失败'}), 500

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



if __name__ == '__main__':
    # 启动 Flask 开发服务器
    logger.info("启动 Flask API 服务器...")
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False,
        use_reloader=False,  # 禁用重新加载器，避免 PyWebView 中的问题
        threaded=True         # 提升并发处理能力
    )
