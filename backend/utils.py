"""
工具函数模块
提供项目中共用的辅助函数，避免多处重复实现
"""

import hashlib
import logging
import socket
from pathlib import Path
from typing import Optional, Union, Tuple

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """获取局域网 IP（通过 UDP socket 探测路由，连接外部地址但不实际发包）

    Returns:
        本机局域网 IP，失败时返回 127.0.0.1
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def get_file_fingerprint(path: Union[str, Path]) -> Optional[Tuple[int, float]]:
    """获取文件快速指纹（大小 + 修改时间）

    用于快速预筛，两个文件如果指纹不同则不可能内容相同。

    Args:
        path: 文件路径

    Returns:
        (文件大小, 修改时间戳) 元组，失败返回 None
    """
    try:
        stat = Path(path).stat()
        return (stat.st_size, stat.st_mtime)
    except Exception as e:
        logger.debug(f"获取文件指纹失败 [{path}]: {e}")
        return None


def compute_md5(path: Union[str, Path], chunk_size: int = 1024 * 1024) -> Optional[str]:
    """计算文件 MD5 哈希值

    Args:
        path: 文件路径（str 或 Path）
        chunk_size: 读取块大小，默认 1MB

    Returns:
        32 位小写十六进制 MD5 字符串，失败时返回 None
    """
    try:
        hasher = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"计算 MD5 失败 [{path}]: {e}")
        return None
