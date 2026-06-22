"""
mDNS 服务广播器 - 供 MobileAccessServer 调用
依赖: zeroconf>=0.132.0
"""
from __future__ import annotations

import logging
import socket
import threading
from pathlib import Path

from zeroconf import ServiceInfo, Zeroconf

from .utils import get_local_ip

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_blurarc._tcp.local."
SERVICE_NAME_TEMPLATE = "Blur Arc on {hostname}._blurarc._tcp.local."


class ZeroconfPublisher:
    """mDNS 服务广播器

    start() 为异步（后台线程），调用 wait_ready(timeout) 可确认广播是否成功启动。
    """

    def __init__(self, port: int, app_name: str = "Blur Arc"):
        self.port = port
        self.app_name = app_name
        self._zc: Zeroconf | None = None
        self._info: ServiceInfo | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._last_error: str | None = None

    def start(self) -> None:
        """开始广播（异步，不阻塞主线程）"""
        if self._zc is not None:
            logger.warning("[Zeroconf] 已在广播中")
            return

        self._ready.clear()
        self._last_error = None

        def _run():
            try:
                local_ip = get_local_ip()
                address = socket.inet_aton(local_ip)
                hostname = socket.gethostname()

                self._info = ServiceInfo(
                    SERVICE_TYPE,
                    SERVICE_NAME_TEMPLATE.format(hostname=hostname),
                    port=self.port,
                    addresses=[address],
                    properties={
                        "app": self.app_name,
                        "version": "1.0",
                        "hostname": hostname,
                    },
                )
                self._zc = Zeroconf()
                self._zc.register_service(self._info)
                self._ready.set()
                logger.info(f"[Zeroconf] 广播已启动: {local_ip}:{self.port}")
            except Exception as e:
                self._last_error = str(e)
                logger.error(f"[Zeroconf] 启动失败: {e}")

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def wait_ready(self, timeout: float = 3.0) -> bool:
        """等待广播就绪，返回 True 表示成功，False 表示超时或失败"""
        if not self._ready.wait(timeout):
            if self._last_error:
                logger.error(f"[Zeroconf] 广播启动失败: {self._last_error}")
            else:
                logger.warning(f"[Zeroconf] 广播启动超时 ({timeout}s)")
            return False
        return True

    def stop(self) -> None:
        """停止广播"""
        if self._zc is None:
            return

        # 分步清理：unregister 失败也要尝试 close()
        zc = self._zc
        self._zc = None
        self._info = None
        self._ready.clear()

        try:
            zc.unregister_all_services()
            logger.info("[Zeroconf] 服务已取消注册")
        except Exception as e:
            logger.warning(f"[Zeroconf] 取消注册失败（继续关闭）: {e}")

        try:
            zc.close()
            logger.info("[Zeroconf] 广播已停止")
        except Exception as e:
            logger.error(f"[Zeroconf] 关闭失败: {e}")

    def is_running(self) -> bool:
        return self._zc is not None and self._ready.is_set()
