"""
目标文件名生成（含原子计数器）
================================

**为什么需要这个模块？**

v0.6 优化 6：将原 ``_build_dest_filename`` 的 O(n) 文件系统探测 + 多线程 TOCTOU 重试
替换为 O(1) 进程级原子计数器。

**核心机制：**

- ``itertools.count(1)`` 进程级原子计数器（CPython GIL 保证 next() 原子性）
- ``threading.Lock`` 保护 ``taken_names`` 集合的并发读写
- ``build_dest_filename`` 接受 ``taken_names`` 参数，由 import_manager 在锁内维护
- 命名格式保持向后兼容：``YYYYMMDD_HHmmss_NNN[_dup].ext``

**典型用法：**

.. code-block:: python

    from backend.dest_filename import build_dest_filename, reset_counter

    taken = set()  # 在 ImportManager 内部维护（每个导入任务一个）
    for media_date, ext in photo_list:
        dest = build_dest_filename(media_date, ext, month_dir, is_dup=False, taken_names=taken)
        shutil.copy2(src, dest)
"""
import itertools
import threading
from pathlib import Path
from datetime import datetime
from typing import Set


# 进程级原子计数器（从 1 开始）
_seq_counter = itertools.count(1)

# 用于保护 taken_names 的锁
_filename_lock = threading.Lock()


def reset_counter() -> None:
    """重置计数器（仅测试用）"""
    global _seq_counter
    _seq_counter = itertools.count(1)


def _next_seq() -> int:
    """获取下一个序号（O(1)，CPython GIL 保证原子性）"""
    return next(_seq_counter)


def build_dest_filename(
    media_date: datetime,
    ext: str,
    month_dir: Path,
    is_dup: bool,
    taken_names: Set[str],
) -> Path:
    """
    生成目标文件名（线程安全，O(1)）

    Args:
        media_date: datetime 对象（决定 stem）
        ext: 扩展名（.jpg / .mp4 等，带前导点）
        month_dir: 目标月份目录（YYYY-MM/）
        is_dup: 是否为重复文件（True → 加 _dup 后缀）
        taken_names: 已被占用的文件名集合（线程间共享，由调用者维护）

    Returns:
        完整的目标文件路径（month_dir / filename）

    命名格式：

    - ``20240315_143022_001.jpg``
    - ``20240315_143022_002_dup.jpg`` （is_dup=True）
    """
    stem = media_date.strftime("%Y%m%d_%H%M%S")
    with _filename_lock:
        while True:
            n = _next_seq()
            if is_dup:
                candidate = f"{stem}_{n:03d}_dup{ext}"
            else:
                candidate = f"{stem}_{n:03d}{ext}"
            if candidate not in taken_names:
                taken_names.add(candidate)
                return month_dir / candidate
