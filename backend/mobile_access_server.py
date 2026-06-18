"""
移动接入服务 - 独立端口 Flask 实例
供 Flutter App 浏览相册和推送照片
"""
from __future__ import annotations

import io
import json
import logging
import os
import secrets
import socket
import string
import threading
import time
import uuid
import shutil
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

import qrcode
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.serving import make_server
from werkzeug.utils import secure_filename

from .config_manager import _get_app_data_dir, ConfigManager
from .constants import MEDIA_FORMATS
from .zeroconf_publisher import ZeroconfPublisher

logger = logging.getLogger(__name__)

APP_DATA_DIR = _get_app_data_dir()
TOKENS_FILE = APP_DATA_DIR / ".config" / "mobile_tokens.json"
UPLOAD_ROOT = APP_DATA_DIR / ".config" / "phone_upload"
MAX_SINGLE_FILE_BYTES = 500 * 1024 * 1024
MAX_FILES_PER_SESSION = 2000
PAIR_RATE_LIMIT = 10  # 每个 IP 每分钟最多请求 10 次配对
PAIR_RATE_WINDOW = 60  # 速率限制窗口（秒）
ALLOWED_EXTENSIONS = MEDIA_FORMATS


class PairingManager:
    """配对码管理器（新流程：mDNS 发现 → 配对码验证）
    
    线程安全说明：PairingManager 同时被主 Flask 线程（threaded=True）和移动接入服务线程
    （threaded=False）访问，因此所有读写共享状态的方法均使用 self._lock 保护。
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._current_code: str | None = None
        self._code_expires_at: float = 0.0
        self._pending: PendingPairing | None = None
        self._confirmed_devices: list[dict] = []

    def _generate_code_unlocked(self) -> str:
        """内部：生成配对码（调用方必须持有 self._lock）"""
        self._current_code = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(PAIRING_CODE_LENGTH)
        )
        self._code_expires_at = time.time() + PAIRING_CODE_TTL
        logger.info(f"[Pairing] 生成配对码: {self._current_code}")
        return self._current_code

    def generate_code(self) -> str:
        """生成新的配对码（PC 端确认配对时调用）"""
        with self._lock:
            return self._generate_code_unlocked()

    def verify_code(self, code: str) -> bool:
        """验证配对码（手机端提交时调用）"""
        with self._lock:
            if time.time() > self._code_expires_at:
                logger.warning("[Pairing] 配对码已过期")
                return False
            if self._current_code is None:
                return False
            result = secrets.compare_digest(self._current_code, code.upper())
            if result:
                logger.info("[Pairing] 配对码验证成功")
            else:
                logger.warning("[Pairing] 配对码验证失败")
            return result

    def consume_code(self) -> None:
        """验证成功后消费掉配对码（一次性）"""
        with self._lock:
            self._current_code = None
            self._code_expires_at = 0.0

    def set_pending(self, device_name: str) -> None:
        """设置待确认设备"""
        with self._lock:
            self._pending = PendingPairing(device_name=device_name, requested_at=time.time())

    def get_pending(self) -> PendingPairing | None:
        """获取待确认设备（PC 端轮询用）"""
        with self._lock:
            if self._pending and self._pending.status == "pending":
                return self._pending
            return None

    def confirm_pending(self) -> str:
        """确认配对 → 生成配对码并返回"""
        with self._lock:
            if not self._pending:
                raise RuntimeError("没有待确认的配对请求")
            self._pending.status = "confirmed"
            return self._generate_code_unlocked()

    def reject_pending(self) -> None:
        """拒绝配对"""
        with self._lock:
            if self._pending:
                self._pending.status = "rejected"

    def clear_pending(self) -> None:
        """清除待确认状态"""
        with self._lock:
            self._pending = None

    def is_code_valid(self) -> bool:
        """配对码是否在有效期内"""
        with self._lock:
            return time.time() <= self._code_expires_at and self._current_code is not None


@dataclass
class PendingPairing:
    """待确认的配对请求"""
    device_name: str
    requested_at: float
    status: str = "pending"  # pending | confirmed | rejected


PAIRING_CODE_LENGTH = 6
PAIRING_CODE_TTL = 120  # 秒


class TokenManager:
    """令牌管理器 - 负责配对、验证、持久化"""

    def __init__(self):
        self._pending_codes: dict[str, dict] = {}
        self._tokens: dict[str, dict] = {}
        self._device_map: dict[str, str] = {}
        self._upload_counts: dict[str, int] = {}  # token → 本会话上传计数
        self._load_tokens()

    def _cleanup_expired_pending(self) -> None:
        """清理已过期的 pending 码（60 秒超时）- 内部方法"""
        now = time.time()
        expired = [
            k for k, v in self._pending_codes.items()
            if v.get("accepted") is not True and now - v.get("created_at", 0) > 60
        ]
        for k in expired:
            self._pending_codes.pop(k, None)
        if expired:
            logger.debug(f"[TokenManager] 清理了 {len(expired)} 个过期 pending 码")

    def generate_pairing_code(self) -> tuple[str, str]:
        self._cleanup_expired_pending()
        code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        self._pending_codes[code] = {"device_name": None, "created_at": time.time()}
        return code, code

    def handle_pair_request(self, pairing_code: str, device_name: str) -> dict | None:
        self._cleanup_expired_pending()
        pending = self._pending_codes.get(pairing_code)
        if not pending or pending.get("accepted") is True:
            return None
        if time.time() - pending.get("created_at", 0) > 60:
            self._pending_codes.pop(pairing_code, None)
            return None
        pending["device_name"] = device_name
        pending["accepted"] = False
        return {"code": pairing_code, "device_name": device_name}

    def confirm_pair_request(self, pairing_code: str) -> str | None:
        self._cleanup_expired_pending()
        pending = self._pending_codes.get(pairing_code)
        if not pending or pending.get("accepted") is not False:
            return None
        device_name = pending.get("device_name", "未知设备")
        # 同一设备重配对：先撤销旧 token，确保新旧不会并存
        old_token = self._device_map.get(device_name)
        if old_token and old_token in self._tokens:
            self._tokens.pop(old_token)
        token = uuid.uuid4().hex
        self._tokens[token] = {"device_name": device_name, "paired_at": datetime.now().isoformat()}
        self._device_map[device_name] = token
        pending["accepted"] = True
        self._save_tokens()
        return token

    def reject_pair_request(self, pairing_code: str):
        self._pending_codes.pop(pairing_code, None)

    def validate_token(self, token: str) -> bool:
        return token in self._tokens

    def get_device_name(self, token: str) -> str:
        return self._tokens.get(token, {}).get("device_name", "未知设备")

    def generate_token(self, device_name: str) -> str:
        """为已配对的设备生成 token（新流程：配对码验证成功后调用）"""
        # 同一设备重配对：先撤销旧 token
        old_token = self._device_map.get(device_name)
        if old_token and old_token in self._tokens:
            self._tokens.pop(old_token)
        token = uuid.uuid4().hex
        self._tokens[token] = {"device_name": device_name, "paired_at": datetime.now().isoformat()}
        self._device_map[device_name] = token
        self._save_tokens()
        return token

    def revoke_token(self, token: str):
        device_name = self._tokens.pop(token, {}).get("device_name", "")
        if device_name:
            self._device_map.pop(device_name, None)
        self._save_tokens()

    def revoke_all(self):
        self._tokens.clear()
        self._device_map.clear()
        self._save_tokens()

    def get_paired_devices(self) -> list[dict]:
        return [{"token": t, **info} for t, info in self._tokens.items()]

    def get_pending_pair_code(self) -> str | None:
        for code, info in self._pending_codes.items():
            if info.get("accepted") is False:
                return code
        return None

    def get_pending_device_name(self, code: str) -> str:
        pending = self._pending_codes.get(code, {})
        return pending.get("device_name", "未知设备")

    def _load_tokens(self):
        if TOKENS_FILE.exists():
            try:
                data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
                self._tokens = data.get("tokens", {})
                self._device_map = data.get("device_map", {})
            except Exception:
                pass

    def _save_tokens(self):
        TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKENS_FILE.write_text(json.dumps({
            "tokens": self._tokens, "device_map": self._device_map,
        }, indent=2, ensure_ascii=False), encoding="utf-8")


class MobileAccessServer:
    """移动接入服务"""

    PORT_RANGE = (8900, 8999)

    def __init__(self):
        self.app = Flask(__name__)
        self.app.config['MAX_CONTENT_LENGTH'] = MAX_SINGLE_FILE_BYTES  # Werkzeug 全局上传限制
        # CORS：允许 Flutter App 从任意源访问移动接入服务
        CORS(self.app, resources={r"/api/mobile/*": {"origins": "*"},
                                  r"/pair": {"origins": "*"},
                                  r"/api/mobile/pair-request": {"origins": "*"},
                                  r"/api/mobile/pair-status": {"origins": "*"}},
             supports_credentials=False)
        self.port: int | None = None
        self._local_ip: str = "127.0.0.1"
        self._server = None
        self._thread: threading.Thread | None = None
        self.token_manager = TokenManager()
        self._pairing = PairingManager()
        self._zeroconf: ZeroconfPublisher | None = None
        self._pair_rate_limits: dict[str, list[float]] = {}  # IP → 请求时间戳列表
        self._register_routes()

    def _register_routes(self):

        def _check_pair_rate_limit() -> bool:
            """检查 IP 是否超过配对请求速率限制"""
            ip = request.remote_addr or "0.0.0.0"
            now = time.time()
            timestamps = self._pair_rate_limits.get(ip, [])
            # 清除过期记录
            timestamps = [t for t in timestamps if now - t < PAIR_RATE_WINDOW]
            self._pair_rate_limits[ip] = timestamps
            if len(timestamps) >= PAIR_RATE_LIMIT:
                return False  # 超限
            timestamps.append(now)
            return True  # 允许

        @self.app.route("/pair", methods=["GET"])
        def pair_qr():
            if not _check_pair_rate_limit():
                return jsonify({"error": "配对请求过于频繁，请稍后再试"}), 429
            code, qr_content = self.token_manager.generate_pairing_code()
            return jsonify({"pairing_code": code, "qr": qr_content})

        @self.app.route("/api/mobile/pair-request", methods=["POST"])
        def pair_request():
            if not _check_pair_rate_limit():
                return jsonify({"error": "配对请求过于频繁，请稍后再试"}), 429
            data = request.get_json(force=True, silent=True) or {}
            code = data.get("code", "")
            device_name = data.get("device_name", "未知设备")
            result = self.token_manager.handle_pair_request(code, device_name)
            if result:
                return jsonify({"status": "pending", "device_name": device_name})
            return jsonify({"error": "配对码无效或已过期"}), 400

        @self.app.route("/api/mobile/pair-status", methods=["GET"])
        def pair_status():
            """移动端轮询配对状态，桌面端确认后返回 token"""
            code = request.args.get("code", "")
            pending = self.token_manager._pending_codes.get(code)
            if not pending:
                return jsonify({"status": "invalid"}), 404
            if pending.get("accepted") is True:
                device_name = pending.get("device_name", "未知设备")
                token = self.token_manager._device_map.get(device_name)
                if token:
                    # 配对成功，清理 pending 码
                    self.token_manager._pending_codes.pop(code, None)
                    return jsonify({"status": "accepted", "token": token})
            if time.time() - pending.get("created_at", 0) > 60:
                self.token_manager._pending_codes.pop(code, None)
                return jsonify({"status": "expired"}), 410
            return jsonify({"status": "pending"})

        @self.app.route("/api/mobile/verify")
        def verify_token():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return jsonify({"error": "令牌无效"}), 401
            return jsonify({"status": "ok", "app_version": "1.0", "name": "Blur Arc"})

        @self.app.route("/api/mobile/stats")
        def mobile_stats():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return jsonify({"error": "令牌无效"}), 401
            try:
                from .api_server import get_album_stats as _get_stats
                return jsonify(_get_stats() or {"total_files": 0})
            except Exception:
                return jsonify(self._fallback_stats())

        @self.app.route("/api/mobile/tree")
        def mobile_tree():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return jsonify({"error": "令牌无效"}), 401
            try:
                from .api_server import get_album_path, MEDIA_FORMATS as _MEDIA_FMTS
                import os as _os
                album_path = get_album_path()
                if not album_path or not Path(album_path).exists():
                    return jsonify({"children": []})
                from pathlib import Path as _Path
                root = {"name": _Path(album_path).name, "path": album_path, "type": "root", "count": 0, "children": []}
                stack = [(album_path, root, [], False)]
                while stack:
                    dirpath, parent, _, processed = stack.pop()
                    if processed:
                        parent["count"] = sum(
                            (c.get("count", 0) for c in parent.get("children", [])),
                            sum(1 for e in _os.scandir(dirpath)
                                if e.is_file() and Path(e.name).suffix.lower() in _MEDIA_FMTS)
                        )
                        continue
                    stack.append((dirpath, parent, [], True))
                    children = []
                    try:
                        for entry in _os.scandir(dirpath):
                            if entry.is_dir():
                                node = {"name": entry.name, "path": entry.path, "type": "directory", "count": 0, "children": []}
                                children.append(node)
                                stack.append((entry.path, node, [], False))
                    except PermissionError:
                        pass
                    parent["children"] = sorted(children, key=lambda x: x["name"])
                return jsonify(root)
            except Exception:
                return jsonify({"children": []})

        @self.app.route("/api/mobile/photos")
        def mobile_photos():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            if not path or not path.strip():
                return jsonify({"photos": [], "count": 0})
            page = int(request.args.get("page", 1))
            page_size = int(request.args.get("page_size", 100))
            try:
                from .api_server import get_album_path, MEDIA_FORMATS as _MEDIA_FMTS
                album_path = get_album_path()
                if not album_path:
                    return jsonify({"photos": [], "count": 0})
                target = Path(path).resolve()
                album_resolved = Path(album_path).resolve()
                # Windows 路径不区分大小写，需使用 lower 比较
                if os.name == 'nt':
                    if not str(target).lower().startswith(str(album_resolved).lower()):
                        return jsonify({"photos": [], "count": 0})
                else:
                    if not target.is_relative_to(album_resolved):
                        return jsonify({"photos": [], "count": 0})
                if not target.exists() or not target.is_dir():
                    return jsonify({"photos": [], "count": 0})
                files = []
                for f in sorted(target.iterdir()):
                    if f.is_file() and f.suffix.lower() in _MEDIA_FMTS:
                        files.append({
                            "id": f.name, "name": f.name, "path": str(f),
                            "size": f.stat().st_size, "date": "", "type": "photo",
                        })
                total = len(files)
                start = (page - 1) * page_size
                end = start + page_size
                return jsonify({"photos": files[start:end], "count": total, "total_pages": (total + page_size - 1) // page_size})
            except Exception:
                return jsonify({"photos": [], "count": 0})

        @self.app.route("/api/mobile/thumbnail")
        def mobile_thumbnail():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            try:
                from .thumbnail_manager import get_thumbnail_sync
                from .api_server import get_album_path
                album_path = get_album_path()
                if not album_path or not Path(path).resolve().is_relative_to(Path(album_path).resolve()):
                    return jsonify({"error": "路径不在相册目录下"}), 403
                thumb_path = get_thumbnail_sync(path)
                if thumb_path and Path(thumb_path).exists():
                    return send_file(str(thumb_path), mimetype='image/jpeg')
                return jsonify({"error": "无法生成缩略图"}), 500
            except Exception:
                return jsonify({"error": "获取缩略图失败"}), 500

        @self.app.route("/api/mobile/file")
        def mobile_file():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            try:
                from .api_server import get_album_path
                album_path = get_album_path()
                if not album_path or not Path(path).resolve().is_relative_to(Path(album_path).resolve()):
                    return jsonify({"error": "路径不在相册目录下"}), 403
                ext = Path(path).suffix.lower()
                mime_map = {
                    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                    '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
                    '.mp4': 'video/mp4', '.mkv': 'video/x-matroska', '.avi': 'video/x-msvideo',
                    '.mov': 'video/quicktime', '.webm': 'video/webm',
                }
                return send_file(str(Path(path)), mimetype=mime_map.get(ext, 'application/octet-stream'), conditional=True)
            except Exception:
                return jsonify({"error": "获取文件失败"}), 500

        @self.app.route("/api/mobile/preview")
        def mobile_preview():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            try:
                from .api_server import get_album_path
                album_path = get_album_path()
                if not album_path or not Path(path).resolve().is_relative_to(Path(album_path).resolve()):
                    return jsonify({"error": "路径不在相册目录下"}), 403
                ext = Path(path).suffix.lower()
                if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
                    return send_file(str(Path(path)), mimetype='image/jpeg')
                from .thumbnail_manager import get_preview_jpeg
                preview_path = get_preview_jpeg(path)
                if preview_path and Path(preview_path).exists():
                    return send_file(str(preview_path), mimetype='image/jpeg')
                return send_file(str(Path(path)), mimetype='application/octet-stream')
            except Exception:
                return jsonify({"error": "获取预览图失败"}), 500

        @self.app.route("/api/mobile/exif")
        def mobile_exif():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            try:
                from .api_server import get_album_path
                album_path = get_album_path()
                if not album_path or not Path(path).resolve().is_relative_to(Path(album_path).resolve()):
                    return jsonify({"error": "路径不在相册目录下"}), 403
                from PIL import Image
                from PIL.ExifTags import TAGS
                img = Image.open(path)
                exif_raw = img._getexif() or {}
                exif = {}
                for k, v in exif_raw.items():
                    tag = TAGS.get(k, k)
                    if isinstance(v, bytes):
                        try: v = v.decode('utf-8', errors='replace')
                        except: continue
                    exif[tag] = v
                gps_info = exif_raw.get(34853) or {}
                gps = {}
                if gps_info:
                    def _to_decimal(d, m, s):
                        try: return float(d) + float(m) / 60 + float(s) / 3600
                        except: return 0
                    gps = {
                        "lat": _to_decimal(*gps_info.get(2, [0, 0, 0])) if 2 in gps_info else 0,
                        "lng": _to_decimal(*gps_info.get(4, [0, 0, 0])) if 4 in gps_info else 0,
                    }
                return jsonify({
                    "make": exif.get("Make", ""),
                    "model": exif.get("Model", ""),
                    "datetime": exif.get("DateTimeOriginal", ""),
                    "focal_length": str(exif.get("FocalLength", "")),
                    "f_number": str(exif.get("FNumber", "")),
                    "iso": exif.get("ISOSpeedRatings", ""),
                    "gps": gps,
                })
            except Exception:
                return jsonify({"error": "获取 EXIF 失败"}), 500

        @self.app.route("/api/mobile/upload", methods=["POST"])
        def mobile_upload():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return jsonify({"error": "令牌无效"}), 401
            return self._handle_upload(token)

        # ============== 重设计配对端点（mDNS 发现流程） ==============

        @self.app.route("/api/mobile/pairing/request", methods=["POST"])
        def pairing_request():
            """手机端发起配对请求"""
            data = request.get_json(force=True, silent=True) or {}
            device_name = data.get("device_name", "Unknown")
            
            # 输入验证：限制设备名长度和内容
            device_name = device_name.strip() if isinstance(device_name, str) else ""
            if not device_name:
                return jsonify({"error": "设备名不能为空"}), 400
            if len(device_name) > 50:
                return jsonify({"error": "设备名长度不能超过 50 个字符"}), 400
            if any(c in device_name for c in ('/', '\\', '\0')):
                return jsonify({"error": "设备名包含非法字符"}), 400

            if self._pairing.get_pending() is not None:
                return jsonify({"error": "已有待确认的配对请求"}), 409

            self._pairing.set_pending(device_name)
            logger.info(f"[Pairing] 收到配对请求: {device_name}")
            return jsonify({"status": "requested"})

        @self.app.route("/api/mobile/pairing/pending", methods=["GET"])
        def pairing_pending():
            """PC 端轮询是否有待确认的配对请求"""
            pending = self._pairing.get_pending()
            if pending is None:
                return jsonify({"status": "none"})
            return jsonify({
                "status": "pending",
                "device_name": pending.device_name,
                "requested_at": pending.requested_at,
            })

        @self.app.route("/api/mobile/pairing/confirm", methods=["POST"])
        def pairing_confirm():
            """PC 端确认配对 → 生成配对码"""
            if self._pairing.get_pending() is None:
                return jsonify({"error": "没有待确认的配对请求"}), 404
            code = self._pairing.confirm_pending()
            return jsonify({
                "status": "confirmed",
                "pairing_code": code,
                "expires_in": PAIRING_CODE_TTL,
            })

        @self.app.route("/api/mobile/pairing/reject", methods=["POST"])
        def pairing_reject():
            """PC 端拒绝配对"""
            self._pairing.reject_pending()
            return jsonify({"status": "rejected"})

        @self.app.route("/api/mobile/pairing/submit-code", methods=["POST"])
        def pairing_submit_code():
            """手机端提交配对码"""
            data = request.get_json(force=True, silent=True) or {}
            code = data.get("code", "")
            device_name = data.get("device_name", "")

            if not self._pairing.verify_code(code.upper()):
                return jsonify({"status": "invalid", "error": "配对码错误或已过期"}), 400

            # 验证成功 → 生成 token
            self._pairing.consume_code()
            token = self.token_manager.generate_token(device_name)
            self._pairing.clear_pending()

            # 停止配对模式（配对完成）
            self.stop_pairing_mode()

            return jsonify({"status": "paired", "token": token})

    def _extract_token(self) -> str | None:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return None

    def _handle_upload(self, token: str):
        # 1. Content-Length 预检 — 拒绝超大请求，避免写入磁盘后才检查
        content_length = request.content_length
        if content_length and content_length > MAX_SINGLE_FILE_BYTES:
            return jsonify({"error": "文件超过大小限制 (500MB)"}), 413

        # 2. Session 文件计数限制
        count = self.token_manager._upload_counts.get(token, 0)
        if count >= MAX_FILES_PER_SESSION:
            return jsonify({"error": "本会话上传文件数已达上限"}), 429

        # 3. 基本验证
        if "file" not in request.files:
            return jsonify({"error": "缺少文件"}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "文件名为空"}), 400
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": f"不支持的文件格式: {ext}"}), 400

        # 4. 安全保存
        safe_name = secure_filename(file.filename) or f"upload_{uuid.uuid4().hex[:8]}{ext}"
        upload_dir = self.token_manager.get_upload_root()
        save_path = upload_dir / safe_name
        counter = 1
        while save_path.exists():
            save_path = upload_dir / f"{Path(safe_name).stem}_{counter}{ext}"
            counter += 1
        try:
            file.save(str(save_path))
        except Exception:
            return jsonify({"error": "文件保存失败"}), 507

        # 5. 写后验证大小
        file_size = save_path.stat().st_size
        if file_size > MAX_SINGLE_FILE_BYTES:
            save_path.unlink()
            return jsonify({"error": "文件超过大小限制 (500MB)"}), 413

        # 6. 更新 session 计数
        self.token_manager._upload_counts[token] = count + 1

        device_name = self.token_manager.get_device_name(token)
        return jsonify({
            "status": "ok", "name": file.filename, "size": file_size,
            "device_name": device_name, "upload_dir": str(upload_dir),
        })

    def start(self) -> dict:
        self._local_ip = self._get_local_ip()
        self.port = self._find_free_port()
        self._server = make_server(self._local_ip, self.port, self.app, threaded=False)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info(f"[MobileAccess] 服务已启动: {self._local_ip}:{self.port}")
        return {"port": self.port, "local_ip": self._local_ip, "service_url": f"http://{self._local_ip}:{self.port}"}

    def stop(self):
        if self._server:
            self._server.shutdown()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._server = None
        self._thread = None
        self.port = None
        logger.info("[MobileAccess] 服务已停止")

    def start_pairing_mode(self) -> dict:
        """开启配对模式：启动 mDNS 广播"""
        if self._zeroconf is None:
            self._zeroconf = ZeroconfPublisher(self.port)
        self._zeroconf.start()
        return {"status": "broadcasting", "hostname": socket.gethostname()}

    def stop_pairing_mode(self) -> None:
        """停止配对模式：停止 mDNS 广播，清除待确认"""
        if self._zeroconf:
            self._zeroconf.stop()
            self._zeroconf = None
        self._pairing.clear_pending()
        self._pairing.consume_code()  # 使当前配对码失效

    def _find_free_port(self) -> int:
        for port in range(self.PORT_RANGE[0], self.PORT_RANGE[1] + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    return port
        raise RuntimeError(f"端口范围 {self.PORT_RANGE} 内没有可用端口")

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def has_paired_devices(self) -> bool:
        return len(self.token_manager.get_paired_devices()) > 0

    def _fallback_stats(self):
        try:
            cm = ConfigManager()
            album_path = cm.get_setting("album_path")
            if not album_path or not Path(album_path).exists():
                return {"total_files": 0, "total_size_mb": 0}
            total = 0
            total_size = 0
            for p in Path(album_path).rglob("*"):
                if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
                    total += 1
                    total_size += p.stat().st_size
            return {"total_files": total, "total_size_mb": round(total_size / (1024**2), 2)}
        except Exception:
            return {"total_files": 0, "total_size_mb": 0}


def generate_mobile_qr(code: str, ip: str, port: int) -> bytes:
    url = f"blurarc://pair?code={code}&host={ip}&port={port}"
    img = qrcode.make(url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()
