"""
视频处理模块 - 封装FFmpeg功能
使用本地集成的FFmpeg二进制文件，无需外部下载
提供视频缩略图生成、元数据提取等功能
"""

import os
import sys
import logging
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# ---------------------------------------------------------------------------
# Windows 无窗口运行子进程
# ---------------------------------------------------------------------------
# subprocess.run/Popen 在 Windows 默认创建新控制台窗口（闪烁后消失）。
# 通过设置 CREATE_NO_WINDOW 标志（Win32 API）可以完全抑制窗口创建。
# 非 Windows 平台不需要此标志。
_NO_CONSOLE_FLAGS: int = 0
if sys.platform == 'win32':
    try:
        _NO_CONSOLE_FLAGS = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    except AttributeError:
        # 旧 Python 版本没有 CREATE_NO_WINDOW 常量，直接使用 Win32 值
        _NO_CONSOLE_FLAGS = 0x08000000  # CREATE_NO_WINDOW

def _run_subprocess_silent(cmd, **kwargs):
    """执行子进程但不创建新控制台窗口（Windows）。
    在非 Windows 平台上等价于 subprocess.run。
    """
    if sys.platform == 'win32':
        # 合并调用方可能已设置的其他 creationflags
        existing = kwargs.pop('creationflags', 0) or 0
        kwargs['creationflags'] = existing | _NO_CONSOLE_FLAGS
    return subprocess.run(cmd, **kwargs)

# 路径适配：兼容 PyInstaller 打包（sys._MEIPASS）和直接运行两种模式
if getattr(sys, 'frozen', False):
    _BACKEND_BASE = Path(sys._MEIPASS) / 'backend'
else:
    _BACKEND_BASE = Path(__file__).parent

PROJECT_ROOT = Path(__file__).parent.parent

# 优先使用系统级FFmpeg（如果可用），否则使用本地集成的FFmpeg
# 检查系统PATH中是否有ffmpeg和ffprobe
def _find_ffmpeg_in_path():
    """在系统PATH中查找ffmpeg"""
    cmd = 'where' if sys.platform == 'win32' else 'which'
    try:
        result = _run_subprocess_silent([cmd, 'ffmpeg'], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            return Path(lines[0]) if lines else None
    except Exception:
        pass
    return None

def _find_ffprobe_in_path():
    """在系统PATH中查找ffprobe"""
    cmd = 'where' if sys.platform == 'win32' else 'which'
    try:
        result = _run_subprocess_silent([cmd, 'ffprobe'], capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            return Path(lines[0]) if lines else None
    except Exception:
        pass
    return None

# 本地集成的FFmpeg路径（打包后位于 _MEIPASS/backend/ffmpeg_binaries/）
# Windows 使用 .exe 后缀，macOS/Linux 无后缀
_EXE = ".exe" if sys.platform == "win32" else ""
FFMPEG_BIN_DIR = _BACKEND_BASE / "ffmpeg_binaries"
LOCAL_FFMPEG_PATH = FFMPEG_BIN_DIR / f"ffmpeg{_EXE}"
LOCAL_FFPROBE_PATH = FFMPEG_BIN_DIR / f"ffprobe{_EXE}"

# 优先使用系统FFmpeg，如果不可用则使用本地版本
FFMPEG_PATH = _find_ffmpeg_in_path() or LOCAL_FFMPEG_PATH
FFPROBE_PATH = _find_ffprobe_in_path() or LOCAL_FFPROBE_PATH

# 日志配置
logger = logging.getLogger(__name__)

# 启动时检测FFmpeg可用性
if FFMPEG_PATH.exists() and FFPROBE_PATH.exists():
    ffmpeg_source = "系统PATH" if FFMPEG_PATH != LOCAL_FFMPEG_PATH else "本地集成"
    logger.info(f"✅ FFmpeg 可用 ({ffmpeg_source}): ffmpeg={FFMPEG_PATH}, ffprobe={FFPROBE_PATH}")
else:
    logger.warning("⚠️ FFmpeg 不可用 - 视频缩略图和元数据功能将受限")
    logger.warning("  运行 'python scripts/download_ffmpeg.py' 可自动下载集成版本")
    logger.warning("  或将 ffmpeg/ffprobe 添加到系统 PATH")


class VideoProcessor:
    """视频处理器，封装FFmpeg功能，使用本地集成的FFmpeg二进制文件"""
    
    @staticmethod
    def is_ffmpeg_available() -> bool:
        """检查FFmpeg是否可用"""
        return FFMPEG_PATH.exists() and FFPROBE_PATH.exists()
    
    @staticmethod
    def _run_ffmpeg_command(args: list) -> bool:
        """执行FFmpeg命令
        
        Args:
            args: FFmpeg命令参数列表
            
        Returns:
            bool: 执行成功返回True，否则返回False
        """
        try:
            # 确保FFmpeg可用
            if not VideoProcessor.is_ffmpeg_available():
                logger.error("FFmpeg二进制文件不可用")
                return False
            
            # 构建完整命令
            command = [str(FFMPEG_PATH)] + args
            
            # 执行命令（BUG-014：加 timeout=60s，防止损坏视频永久阻塞线程）
            result = _run_subprocess_silent(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg命令执行失败: {' '.join(command)}")
                logger.error(f"错误输出: {result.stderr}")
                return False
            
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg命令超时（>60s），已强制终止: {args[:3]}")
            return False
        except Exception as e:
            logger.error(f"执行FFmpeg命令发生异常: {e}")
            return False
    
    @staticmethod
    def generate_thumbnail(video_path: str, output_path: str, time_seconds: float = 1.0) -> bool:
        """生成视频缩略图
        
        Args:
            video_path: 视频文件路径
            output_path: 缩略图输出路径
            time_seconds: 截取时间点（秒）
            
        Returns:
            bool: 生成成功返回True，否则返回False
        """
        if not VideoProcessor.is_ffmpeg_available():
            logger.error("FFmpeg不可用，无法生成视频缩略图")
            return False
        
        try:
            # 构建FFmpeg命令参数
            args = [
                "-ss", str(time_seconds),  # 截取时间点
                "-i", video_path,          # 输入视频
                "-vframes", "1",           # 只截取一帧
                "-f", "image2",            # 输出格式（image2 管道）
                "-q:v", "2",               # 图片质量（1-31，越小越好）
                "-y",                      # 覆盖输出文件
                output_path                # 输出路径
            ]
            
            return VideoProcessor._run_ffmpeg_command(args)
        except Exception as e:
            logger.error(f"生成视频缩略图发生未知错误: {e}")
            return False
    
    @staticmethod
    def extract_metadata(video_path: str) -> Optional[Dict[str, Any]]:
        """提取视频元数据
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Dict[str, Any]: 视频元数据，如果提取失败返回None
        """
        if not VideoProcessor.is_ffmpeg_available():
            logger.error("FFmpeg不可用，无法提取视频元数据")
            return None
        
        try:
            # 使用本地集成的ffprobe提取视频元数据
            args = [
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            # 执行ffprobe命令
            # BUG-015：加 timeout=30s；不用 text=True，改为手动 utf-8 decode
            # 避免 Windows 中文路径下 text=True 触发 UnicodeDecodeError
            result = subprocess.run(
                [str(FFPROBE_PATH)] + args,
                capture_output=True,
                check=False,
                timeout=30
            )
            
            if result.returncode != 0:
                stderr_msg = result.stderr.decode('utf-8', errors='replace')
                logger.error(f"提取视频元数据失败: {stderr_msg}")
                return None
            
            # 解析JSON输出
            if isinstance(result.stdout, bytes):
                stdout_text = result.stdout.decode('utf-8', errors='replace')
            else:
                stdout_text = result.stdout
            probe_data = json.loads(stdout_text)
            
            if not probe_data or "streams" not in probe_data:
                return None
            
            # 获取视频流信息
            video_stream = next((stream for stream in probe_data["streams"] if stream["codec_type"] == "video"), None)
            if not video_stream:
                return None
            
            # duration 优先取 video_stream，若无则回落到 format 层（部分编码格式如 mkv 只在 format 中携带）
            stream_duration = video_stream.get("duration")
            format_duration = probe_data["format"].get("duration")
            duration_val = float(stream_duration) if stream_duration else (float(format_duration) if format_duration else 0.0)

            metadata = {
                "duration": duration_val,
                "width": int(video_stream.get("width", 0)),
                "height": int(video_stream.get("height", 0)),
                "codec": video_stream.get("codec_name", ""),
                "bit_rate": int(video_stream.get("bit_rate", 0)) if video_stream.get("bit_rate") else 0,
                "frame_rate": video_stream.get("r_frame_rate", "0/1"),
                "format": probe_data["format"].get("format_name", ""),
                "size": int(probe_data["format"].get("size", 0))
            }
            
            # 尝试获取创建时间
            if "tags" in probe_data["format"] and "creation_time" in probe_data["format"]["tags"]:
                try:
                    creation_time = probe_data["format"]["tags"]["creation_time"]
                    # 处理不同的时间格式
                    if "Z" in creation_time:
                        # ISO 8601格式，带Z时区
                        metadata["creation_time"] = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                    else:
                        # 其他格式
                        metadata["creation_time"] = datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
            
            return metadata
            
        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe 提取元数据超时（>30s）: {video_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"解析视频元数据失败: {e}")
            return None
        except Exception as e:
            logger.error(f"提取视频元数据发生未知错误: {e}")
            return None
    
    @staticmethod
    def transcode_video(input_path: str, output_path: str, codec: str = "libx264", quality: int = 23) -> bool:
        """转码视频
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            codec: 视频编码器
            quality: 视频质量（0-51，0为最高质量）
            
        Returns:
            bool: 转码成功返回True，否则返回False
        """
        if not VideoProcessor.is_ffmpeg_available():
            logger.error("FFmpeg不可用，无法转码视频")
            return False
        
        try:
            args = [
                "-i", input_path,
                "-vcodec", codec,
                "-crf", str(quality),
                "-preset", "medium",
                "-y",
                output_path
            ]
            
            return VideoProcessor._run_ffmpeg_command(args)
        except Exception as e:
            logger.error(f"视频转码发生未知错误: {e}")
            return False
    
    @staticmethod
    def get_video_duration(video_path: str) -> Optional[float]:
        """获取视频时长（秒）
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            Optional[float]: 视频时长（秒），如果获取失败返回None
        """
        metadata = VideoProcessor.extract_metadata(video_path)
        if metadata:
            return metadata.get("duration")
        return None
