# Blur Arc 移动端 App — 完整实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Blur Arc 电脑端新增移动接入服务 + 开发 Flutter App（手机/平板），实现局域网相册浏览和照片推送

**Architecture:** 电脑端新增独立 Flask 移动接入服务（8900-8999），令牌验证；Flutter App 自动发现/扫码连接，响应式 UI 适配手机和平板。电脑端和 Flutter App 在同一个 git 仓库。

**Tech Stack:** Python (Flask, qrcode), TypeScript (React 19), Dart/Flutter

---

## ✅ 实现进度总览

> **2026-06-18 更新：** Phase 1-6 代码已完成，Critical 审查问题已修复。Phase 7 端到端联调待真机验证。

| 阶段 | 状态 | 说明 |
|------|------|------|
| **Phase 1** | ✅ 完成 | `mobile_access_server.py` 已创建并更新（含 Critical 修复） |
| **Phase 2** | ✅ 完成 | 桥接端点 + 前端管理面板 + i18n |
| **Phase 3** | ✅ 完成 | BlurArc.py 集成 + 11 个单元测试 PASS |
| **Phase 4** | ✅ 完成 | Flutter 项目骨架 + 连接页面（手动创建，flutter pub get 通过） |
| **Phase 5** | ✅ 完成 | Flutter 相册浏览（tree/grid/preview + 响应式） |
| **Phase 6** | ✅ 完成 | Flutter 推送照片 + 进度追踪 |
| **Phase 7** | ⏳ 待验证 | 端到端联调需要真机/模拟器 |

### Critical 代码审查修复（2026-06-18）

| ID | 问题 | 修复 |
|----|------|------|
| C1 | 缩略图/预览端点 `Path→bytes` 误用（`io.BytesIO(Path)`） | 改为 `send_file(str(path), mimetype='image/jpeg')` |
| C2 | Flutter `pairAndPoll` 协议与后端不匹配，永远拿不到 token | 新增 `/api/mobile/pair-status?code=XXX` 端点 + Flutter pairAndPoll 重写为轮询此端点 |
| C3 | 上传端点无速率/并发控制 | 添加 `MAX_CONTENT_LENGTH=500MB`、content-length 预检(413)、session 文件计数(2000)、`secrets` 替代 `random` |

### Important 代码审查修复

- `mobile_exif` 端点添加路径校验（403 拒绝相册外路径）
- `mobile_photos` 路径校验改为 Windows 大小写不敏感比较（`.lower()`）
- `stop()` 正确 join thread + 重置 port/server/thread
- `_device_map` 持久化保存/加载 + `revoke_token` 清理 `_device_map`

### 已知遗留问题

1. **Flutter 缺少完整 android/ios 目录** — 需运行 `cd blurarc_app && flutter create .` 重新生成
2. **CORS headers 缺失** — 移动服务无 CORS，浏览器直接请求被阻止
3. **`/pair` 端点无 rate limiting** — 可被刷爆配对码
4. **同一 device_name 重配对覆盖旧 token** — 无通知机制
5. **`disable` 不清空 token** — 旧 token 下次启动仍可用
6. **Flutter SDK 安装在 E:\Applications\flutter** — PATH 已配置

---

## 文件结构

```
电脑端新增/修改:
  backend/mobile_access_server.py         # 移动接入服务 + 令牌管理 + 所有端点
  backend/api_server.py                   # 新增 /api/mobile/* 桥接端点
  src/BlurArc.py                          # 集成移动服务启停

  frontend/src/components/dialogs/MobileDeviceManager.tsx
  frontend/src/components/layout/Header.tsx
  frontend/src/services/api.ts
  frontend/src/contexts/I18nContext.tsx

  test/unit/test_mobile_access_server.py

Flutter App (blurarc_app/):
  blurarc_app/pubspec.yaml
  blurarc_app/lib/main.dart
  blurarc_app/lib/services/
  blurarc_app/lib/screens/
  blurarc_app/lib/widgets/
  blurarc_app/lib/models/
```

---

## Flutter App 目录结构

```
blurarc_app/
├── pubspec.yaml
├── lib/
│   ├── main.dart                        # 入口 + 主题 + 路由
│   ├── app.dart                         # MaterialApp + 导航
│   ├── services/
│   │   ├── api_client.dart              # Dio HTTP 客户端 + token 注入
│   │   └── connection_service.dart      # 连接状态管理 + token 持久化
│   ├── models/
│   │   ├── photo.dart                   # 照片数据模型
│   │   └── album_tree.dart              # 目录树数据模型
│   ├── screens/
│   │   ├── connect_screen.dart          # 扫码/手动连接
│   │   ├── album_screen.dart            # 相册首页（响应式布局）
│   │   ├── photo_grid_screen.dart       # 照片网格浏览
│   │   ├── photo_preview_screen.dart    # 全屏预览/视频播放
│   │   └── upload_screen.dart           # 推送照片
│   └── widgets/
│       ├── tree_view.dart               # 年份/月份目录树
│       ├── photo_card.dart              # 缩略图卡片
│       ├── upload_progress.dart         # 上传进度条
│       └── responsive_layout.dart       # 自适应布局组件
└── test/
    └── ...
```

---

## 平板适配要点

| 组件 | 手机 | 平板 |
|------|------|------|
| 相册首页 | 年份列表→点击进入月份→照片网格 | 左侧年份/月份树 + 右侧照片网格(分栏) |
| 照片网格 | 2-3 列 | 4-6 列 |
| 全屏预览 | 全屏沉浸式 | 全屏沉浸式 |
| 推送照片 | 底部 Tab | 底部 Tab 或侧边栏 |
| 弹窗/Modal | 全屏 | 居中弹窗 |

Flutter 本身支持响应式布局（`LayoutBuilder`、`MediaQuery`、`Breakpoint`），一个代码适配两种屏幕尺寸。

---

## 实现阶段

| 阶段 | 内容 | 文件 |
|------|------|------|
| **Phase 1** | `mobile_access_server.py` | 核心服务 + 令牌管理 + 端点 |
| **Phase 2** | 主 API 桥接 + 前端管理面板 | `api_server.py` + `MobileDeviceManager.tsx` + Header |
| **Phase 3** | BlurArc.py 集成 + 测试 | `src/BlurArc.py` + 测试 |
| **Phase 4** | Flutter 项目骨架 + 连接 | 项目创建、扫码/手动连接、token 持久化 |
| **Phase 5** | Flutter 相册浏览 | 目录树、照片网格、全屏预览、视频播放（手机/平板适配） |
| **Phase 6** | Flutter 推送照片 | 相册选择、上传、进度 |
| **Phase 7** | 联调 + 测试 | 端到端 |

---

# Phase 1-3: 电脑端

---

### Task 1: 新增 mobile_access_server.py

**Files:**
- Create: `backend/mobile_access_server.py`

- [ ] **Step 1: Create the module**

```python
"""
移动接入服务 - 独立端口 Flask 实例
供 Flutter App 浏览相册和推送照片
"""
import io
import json
import logging
import os
import random
import socket
import string
import threading
import time
import uuid
import shutil
from pathlib import Path
from datetime import datetime

import qrcode
from flask import Flask, request, jsonify, send_file
from werkzeug.serving import make_server
from werkzeug.utils import secure_filename

from .config_manager import _get_app_data_dir, ConfigManager
from .constants import MEDIA_FORMATS

logger = logging.getLogger(__name__)

APP_DATA_DIR = _get_app_data_dir()
TOKENS_FILE = APP_DATA_DIR / ".config" / "mobile_tokens.json"
UPLOAD_ROOT = APP_DATA_DIR / ".config" / "phone_upload"
MAX_SINGLE_FILE_BYTES = 500 * 1024 * 1024
MAX_FILES_PER_SESSION = 2000
ALLOWED_EXTENSIONS = MEDIA_FORMATS


class TokenManager:
    """令牌管理器 - 负责配对、验证、持久化"""

    def __init__(self):
        self._pending_codes: dict[str, dict] = {}
        self._tokens: dict[str, dict] = {}
        self._device_map: dict[str, str] = {}
        self._load_tokens()

    def generate_pairing_code(self) -> tuple[str, str]:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self._pending_codes[code] = {"device_name": None, "created_at": time.time()}
        return code, code

    def get_upload_root(self) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        d = UPLOAD_ROOT / f"mobile_{ts}_{uuid.uuid4().hex[:8]}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def handle_pair_request(self, pairing_code: str, device_name: str) -> dict | None:
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
        pending = self._pending_codes.get(pairing_code)
        if not pending or pending.get("accepted") is not False:
            return None
        device_name = pending.get("device_name", "未知设备")
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
        self.port: int | None = None
        self._local_ip: str = "127.0.0.1"
        self._server = None
        self._thread: threading.Thread | None = None
        self.token_manager = TokenManager()
        self._register_routes()

    def _register_routes(self):
        @self.app.route("/pair", methods=["GET"])
        def pair_qr():
            code, qr_content = self.token_manager.generate_pairing_code()
            return jsonify({"pairing_code": code, "qr": qr_content})

        @self.app.route("/api/mobile/pair-request", methods=["POST"])
        def pair_request():
            data = request.get_json(force=True, silent=True) or {}
            code = data.get("code", "")
            device_name = data.get("device_name", "未知设备")
            result = self.token_manager.handle_pair_request(code, device_name)
            if result:
                return jsonify({"status": "pending", "device_name": device_name})
            return jsonify({"error": "配对码无效或已过期"}), 400

        # ===== 令牌验证中间件模式 =====
        def require_token():
            token = self._extract_token()
            if not token or not self.token_manager.validate_token(token):
                return None
            return token

        @self.app.route("/api/mobile/verify")
        def verify_token():
            token = require_token()
            if not token:
                return jsonify({"error": "令牌无效"}), 401
            return jsonify({"status": "ok", "app_version": "1.0", "name": "Blur Arc"})

        @self.app.route("/api/mobile/stats")
        def mobile_stats():
            token = require_token()
            if not token:
                return jsonify({"error": "令牌无效"}), 401
            try:
                from .api_server import get_album_stats
                return jsonify(get_album_stats())
            except Exception:
                return jsonify(get_fallback_stats())

        @self.app.route("/api/mobile/tree")
        def mobile_tree():
            token = require_token()
            if not token:
                return jsonify({"error": "令牌无效"}), 401
            try:
                from .api_server import get_album_tree
                return jsonify(get_album_tree())
            except Exception:
                return jsonify({"children": []})

        @self.app.route("/api/mobile/photos")
        def mobile_photos():
            token = require_token()
            if not token:
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            page = int(request.args.get("page", 1))
            page_size = int(request.args.get("page_size", 100))
            try:
                from .api_server import get_photos
                return jsonify(get_photos(path, page, page_size))
            except Exception:
                return jsonify({"photos": [], "count": 0})

        @self.app.route("/api/mobile/thumbnail")
        def mobile_thumbnail():
            token = require_token()
            if not token:
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            try:
                from .api_server import get_thumbnail_file
                return get_thumbnail_file(path)
            except Exception:
                return jsonify({"error": "获取缩略图失败"}), 500

        @self.app.route("/api/mobile/file")
        def mobile_file():
            token = require_token()
            if not token:
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            try:
                from .api_server import serve_file
                return serve_file(path)
            except Exception:
                return jsonify({"error": "获取文件失败"}), 500

        @self.app.route("/api/mobile/preview")
        def mobile_preview():
            token = require_token()
            if not token:
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            try:
                from .api_server import get_preview_file
                return get_preview_file(path)
            except Exception:
                return jsonify({"error": "获取预览图失败"}), 500

        @self.app.route("/api/mobile/exif")
        def mobile_exif():
            token = require_token()
            if not token:
                return jsonify({"error": "令牌无效"}), 401
            path = request.args.get("path", "")
            try:
                from .api_server import get_exif
                return jsonify(get_exif(path))
            except Exception:
                return jsonify({"error": "获取 EXIF 失败"}), 500

        @self.app.route("/api/mobile/upload", methods=["POST"])
        def mobile_upload():
            token = require_token()
            if not token:
                return jsonify({"error": "令牌无效"}), 401
            return self._handle_upload(token)

    def _extract_token(self) -> str | None:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return None

    def _handle_upload(self, token: str):
        if "file" not in request.files:
            return jsonify({"error": "缺少文件"}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "文件名为空"}), 400
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": f"不支持的文件格式: {ext}"}), 400
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
        file_size = save_path.stat().st_size
        if file_size > MAX_SINGLE_FILE_BYTES:
            save_path.unlink()
            return jsonify({"error": "文件超过大小限制"}), 413
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
        logger.info(f"[MobileAccess] 服务已停止 (port={self.port})")

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


def get_fallback_stats():
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
```

- [ ] **Step 2: Verify import**

```bash
cd "F:\AI\Frame_Album" && python -c "from backend.mobile_access_server import MobileAccessServer, TokenManager; print('import ok')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/mobile_access_server.py
git commit -m "feat: add MobileAccessServer with token management and mobile API endpoints"
```

---

### Task 2: 桥接端点 + 前端 API/i18n/Header

**Files:**
- Modify: `backend/api_server.py`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/contexts/I18nContext.tsx`
- Modify: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/dialogs/MobileDeviceManager.tsx`

- [ ] **Step 1: Add mobile control endpoints to api_server.py**

在 `backend/api_server.py` 的 phone-upload 路由之后添加（约第 1196 行后）：

```python
# ============================================================================
# 移动接入 API
# ============================================================================

_mobile_access_server = None

def _get_mobile_server():
    global _mobile_access_server
    if _mobile_access_server is None:
        from .mobile_access_server import MobileAccessServer
        _mobile_access_server = MobileAccessServer()
    return _mobile_access_server


@app.route('/api/mobile/status', methods=['GET'])
def mobile_status():
    try:
        from .mobile_access_server import generate_mobile_qr
        server = _get_mobile_server()
        cm = get_config_manager()
        enabled = cm.get_setting('mobile_service_enabled', False)
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
    try:
        server = _get_mobile_server()
        info = server.start()
        cm = get_config_manager()
        cm.update_setting('mobile_service_enabled', True)
        return jsonify({'status': 'enabled', **info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/disable', methods=['POST'])
def mobile_disable():
    try:
        server = _get_mobile_server()
        server.stop()
        cm = get_config_manager()
        cm.update_setting('mobile_service_enabled', False)
        return jsonify({'status': 'disabled'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/qr', methods=['GET'])
def mobile_qr():
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
    try:
        server = _get_mobile_server()
        code = server.token_manager.get_pending_pair_code()
        if code:
            pending = server.token_manager._pending_codes.get(code, {})
            return jsonify({'hasPending': True, 'pairing_code': code, 'device_name': pending.get('device_name', '未知设备')})
        return jsonify({'hasPending': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/confirm-pairing', methods=['POST'])
def mobile_confirm_pairing():
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
    try:
        server = _get_mobile_server()
        devices = server.token_manager.get_paired_devices()
        return jsonify({'devices': [{'device_name': d['device_name'], 'paired_at': d['paired_at'], 'token': d['token'][:8]+'...'} for d in devices]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/revoke', methods=['POST'])
def mobile_revoke():
    try:
        data = request.get_json(force=True, silent=True) or {}
        server = _get_mobile_server()
        server.token_manager.revoke_token(data.get('token', ''))
        return jsonify({'status': 'revoked'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mobile/revoke-all', methods=['POST'])
def mobile_revoke_all():
    try:
        server = _get_mobile_server()
        server.token_manager.revoke_all()
        return jsonify({'status': 'revoked_all'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 2: Verify import**

```bash
cd "F:\AI\Frame_Album" && python -c "from backend.api_server import app; print('import ok')"
```

- [ ] **Step 3: Add API methods to frontend**

在 `frontend/src/services/api.ts` 的 `api` 对象末尾添加：

```typescript
  // Mobile access service
  getMobileStatus: () =>
    fetchJson<{ enabled: boolean; running: boolean; port: number | null; local_ip: string | null; paired_count: number }>(`${API_BASE}/mobile/status`),

  enableMobileService: () =>
    fetchJson<{ status: string; port: number; local_ip: string }>(`${API_BASE}/mobile/enable`, { method: 'POST' }),

  disableMobileService: () =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/disable`, { method: 'POST' }),

  getMobileQr: () => `${API_BASE}/mobile/qr`,

  getMobilePendingRequest: () =>
    fetchJson<{ hasPending: boolean; pairing_code?: string; device_name?: string }>(`${API_BASE}/mobile/pending-request`),

  confirmMobilePairing: (pairingCode: string, action: 'accept' | 'reject') =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/confirm-pairing`, { method: 'POST', body: JSON.stringify({ pairing_code: pairingCode, action }) }),

  getMobileDevices: () =>
    fetchJson<{ devices: { device_name: string; paired_at: string; token: string }[] }>(`${API_BASE}/mobile/devices`),

  revokeMobileDevice: (token: string) =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/revoke`, { method: 'POST', body: JSON.stringify({ token }) }),

  revokeAllMobileDevices: () =>
    fetchJson<{ status: string }>(`${API_BASE}/mobile/revoke-all`, { method: 'POST' }),
```

- [ ] **Step 4: Add i18n strings**

在 `I18nContext.tsx` 的 zh/en 对象中各添加：

```typescript
    'mobileAccess.title': '移动设备访问',
    'mobileAccess.title_en': 'Mobile Access',
    'mobileAccess.service': '移动接入服务',
    'mobileAccess.service_en': 'Mobile Access Service',
    'mobileAccess.running': '运行中',
    'mobileAccess.running_en': 'Running',
    'mobileAccess.stopped': '已停止',
    'mobileAccess.stopped_en': 'Stopped',
    'mobileAccess.connectionInfo': '连接信息',
    'mobileAccess.connectionInfo_en': 'Connection Info',
    'mobileAccess.newDevice': '新设备配对',
    'mobileAccess.newDevice_en': 'New Device Pairing',
    'mobileAccess.scanQrHint': '使用 Blur Arc App 扫描此二维码',
    'mobileAccess.scanQrHint_en': 'Scan with Blur Arc App',
    'mobileAccess.pairRequest': '请求连接相册',
    'mobileAccess.pairRequest_en': 'Request to connect',
    'mobileAccess.pairedDevices': '已配对设备',
    'mobileAccess.pairedDevices_en': 'Paired Devices',
    'mobileAccess.revoke': '撤销',
    'mobileAccess.revoke_en': 'Revoke',
    'mobileAccess.revokeAll': '撤销全部',
    'mobileAccess.revokeAll_en': 'Revoke All',
    'mobileAccess.entry': '移动设备',
    'mobileAccess.entry_en': 'Mobile',
```

- [ ] **Step 5: Create MobileDeviceManager.tsx**

```tsx
import { useState, useEffect, useCallback } from 'react';
import { Modal } from '../../common/Modal';
import { useI18n } from '../../../contexts/I18nContext';
import { api } from '../../../services/api';

interface PairedDevice {
  device_name: string;
  paired_at: string;
  token: string;
}

interface MobileDeviceManagerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MobileDeviceManager({ isOpen, onClose }: MobileDeviceManagerProps) {
  const { t } = useI18n();
  const [enabled, setEnabled] = useState(false);
  const [running, setRunning] = useState(false);
  const [connectionInfo, setConnectionInfo] = useState<{ local_ip: string; port: number } | null>(null);
  const [pairedDevices, setPairedDevices] = useState<PairedDevice[]>([]);
  const [qrUrl, setQrUrl] = useState('');
  const [pendingRequest, setPendingRequest] = useState<{ device_name: string; pairing_code: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      const status = await api.getMobileStatus();
      setEnabled(status.enabled);
      setRunning(status.running);
      if (status.running && status.local_ip) setConnectionInfo({ local_ip: status.local_ip, port: status.port! });
      if (status.running) {
        const dev = await api.getMobileDevices();
        setPairedDevices(dev.devices);
      }
    } catch {}
  }, []);

  useEffect(() => { if (isOpen) loadStatus(); }, [isOpen, loadStatus]);

  useEffect(() => {
    if (!isOpen || !running) return;
    const interval = setInterval(async () => {
      try {
        const res = await api.getMobilePendingRequest();
        if (res.hasPending) setPendingRequest({ device_name: res.device_name!, pairing_code: res.pairing_code! });
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [isOpen, running]);

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (running) {
        await api.disableMobileService();
        setRunning(false); setEnabled(false); setConnectionInfo(null);
      } else {
        const info = await api.enableMobileService();
        setRunning(true); setEnabled(true);
        setConnectionInfo({ local_ip: info.local_ip, port: info.port });
        setQrUrl(api.getMobileQr());
      }
    } catch {}
    setLoading(false);
  };

  const handleAccept = async () => {
    if (!pendingRequest) return;
    await api.confirmMobilePairing(pendingRequest.pairing_code, 'accept');
    setPendingRequest(null);
    loadStatus();
  };

  const handleReject = async () => {
    if (!pendingRequest) return;
    await api.confirmMobilePairing(pendingRequest.pairing_code, 'reject');
    setPendingRequest(null);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('mobileAccess.title')} size="md">
      <div className="space-y-5">
        <div className="flex items-center justify-between p-4 bg-page rounded-lg border border-border">
          <div>
            <p className="text-sm font-medium">{t('mobileAccess.service')}</p>
            <p className="text-xs text-text-tertiary">{running ? t('mobileAccess.running') : t('mobileAccess.stopped')}</p>
          </div>
          <button onClick={handleToggle} disabled={loading}
            className={`relative w-12 h-6 rounded-full transition-colors ${running ? 'bg-primary' : 'bg-border'}`}>
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${running ? 'translate-x-6' : ''}`} />
          </button>
        </div>

        {running && connectionInfo && (
          <div className="p-3 bg-page rounded-lg border border-border">
            <p className="text-xs text-text-tertiary mb-1">{t('mobileAccess.connectionInfo')}</p>
            <p className="text-sm font-mono text-text-primary">{connectionInfo.local_ip}:{connectionInfo.port}</p>
          </div>
        )}

        {running && (
          <div>
            <p className="text-sm font-medium mb-2">{t('mobileAccess.newDevice')}</p>
            <div className="flex items-start gap-4 p-4 bg-page rounded-lg border border-border">
              <img src={qrUrl} alt="QR" className="w-36 h-36 rounded-md border border-border" />
              <p className="text-xs text-text-tertiary">{t('mobileAccess.scanQrHint')}</p>
            </div>
          </div>
        )}

        {pendingRequest && (
          <div className="p-4 bg-page rounded-lg border-2 border-primary">
            <p className="text-sm font-medium mb-1">{t('mobileAccess.pairRequest')}</p>
            <p className="text-lg font-semibold text-primary mb-3">📱 {pendingRequest.device_name}</p>
            <div className="flex gap-2">
              <button onClick={handleReject} className="flex-1 px-3 py-2 bg-card border border-border rounded-md text-sm hover:border-red-500">{t('common.cancel')}</button>
              <button onClick={handleAccept} className="flex-1 px-3 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover">{t('common.confirm')}</button>
            </div>
          </div>
        )}

        {pairedDevices.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium">{t('mobileAccess.pairedDevices')}</p>
              <button onClick={async () => { await api.revokeAllMobileDevices(); loadStatus(); }} className="text-xs text-red-500">{t('mobileAccess.revokeAll')}</button>
            </div>
            <div className="space-y-2">
              {pairedDevices.map(d => (
                <div key={d.token} className="flex items-center justify-between p-3 bg-page rounded-lg border border-border">
                  <div>
                    <p className="text-sm font-medium">📱 {d.device_name}</p>
                    <p className="text-xs text-text-tertiary">{d.paired_at}</p>
                  </div>
                  <button onClick={async () => { await api.revokeMobileDevice(d.token); loadStatus(); }} className="text-xs text-red-500">{t('mobileAccess.revoke')}</button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
```

- [ ] **Step 6: Update Header.tsx**

在 Header 组件中添加手机按钮和 MobileDeviceManager。

- [ ] **Step 7: Verify TypeScript + build**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- [ ] **Step 8: Commit**

```bash
git add backend/api_server.py frontend/src/services/api.ts frontend/src/contexts/I18nContext.tsx frontend/src/components/dialogs/MobileDeviceManager.tsx frontend/src/components/layout/Header.tsx
git commit -m "feat: add mobile access control endpoints, UI panel, API and i18n"
```

---

### Task 3: BlurArc.py 集成 + 单元测试

**Files:**
- Modify: `src/BlurArc.py`
- Create: `test/unit/test_mobile_access_server.py`

- [ ] **Step 1: 在 BlurArc.py 中读取配置决定自动启动**

在 Flask 服务器就绪后的启动逻辑中添加：

```python
def _start_mobile_service():
    """根据配置自动启动移动接入服务"""
    try:
        from backend.config_manager import ConfigManager
        cm = ConfigManager()
        if cm.get_setting('mobile_service_enabled', False):
            from backend.mobile_access_server import MobileAccessServer
            server = MobileAccessServer()
            info = server.start()
            logger.info(f"移动接入服务已自动启动: {info}")
    except Exception as e:
        logger.warning(f"自动启动移动接入服务失败: {e}")
```

- [ ] **Step 2: Write tests for TokenManager**

```python
"""MobileAccessServer 单元测试"""
import json, time, pytest
from pathlib import Path


class TestTokenManager:
    def test_generate_pairing_code(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, qr = tm.generate_pairing_code()
        assert len(code) == 6 and code == qr

    def test_pair_invalid_code(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        assert tm.handle_pair_request("INVALID", "D") is None

    def test_pair_confirm(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code, "XiaoMi 13")
        token = tm.confirm_pair_request(code)
        assert token and len(token) == 32
        assert tm.validate_token(token)

    def test_pair_reject(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code, "D")
        tm.reject_pair_request(code)
        assert tm.confirm_pair_request(code) is None

    def test_revoke_token(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, _ = tm.generate_pairing_code()
        tm.handle_pair_request(code, "D")
        t = tm.confirm_pair_request(code)
        assert tm.validate_token(t)
        tm.revoke_token(t)
        assert not tm.validate_token(t)

    def test_revoke_all(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        c1, _ = tm.generate_pairing_code(); tm.handle_pair_request(c1, "A"); t1 = tm.confirm_pair_request(c1)
        c2, _ = tm.generate_pairing_code(); tm.handle_pair_request(c2, "B"); t2 = tm.confirm_pair_request(c2)
        assert tm.validate_token(t1) and tm.validate_token(t2)
        tm.revoke_all()
        assert not tm.validate_token(t1) and not tm.validate_token(t2)

    def test_code_expires(self):
        from backend.mobile_access_server import TokenManager
        tm = TokenManager()
        code, _ = tm.generate_pairing_code()
        import time as tmod; tmod.time = lambda: time.time() + 61
        assert tm.handle_pair_request(code, "D") is None


class TestMobileServerLifecycle:
    def test_start_stop(self, monkeypatch, tmp_path):
        import backend.mobile_access_server as mod
        monkeypatch.setattr(mod, "TOKENS_FILE", tmp_path / "tokens.json")
        server = mod.MobileAccessServer()
        info = server.start()
        assert 8900 <= info["port"] <= 8999
        server.stop()

    def test_paired_devices(self, monkeypatch, tmp_path):
        import backend.mobile_access_server as mod
        monkeypatch.setattr(mod, "TOKENS_FILE", tmp_path / "tokens.json")
        server = mod.MobileAccessServer()
        assert not server.has_paired_devices()
        code, _ = server.token_manager.generate_pairing_code()
        server.token_manager.handle_pair_request(code, "T")
        server.token_manager.confirm_pair_request(code)
        assert server.has_paired_devices()
```

- [ ] **Step 3: Run tests**

```bash
cd "F:\AI\Frame_Album" && python -m pytest test/unit/test_mobile_access_server.py -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/BlurArc.py test/unit/test_mobile_access_server.py
git commit -m "feat: auto-start mobile service by config; add unit tests"
```

---

# Phase 4-7: Flutter App

---

### Task 4: Flutter 项目初始化 + 骨架

**Files:**
- Create: `blurarc_app/` (Flutter project)

- [ ] **Step 1: 创建 Flutter 项目**

```bash
cd "F:\AI\Frame_Album" && flutter create --org com.blurarc --project-name blurarc_app blurarc_app
```

- [ ] **Step 2: 添加依赖到 pubspec.yaml**

```yaml
dependencies:
  flutter:
    sdk: flutter
  dio: ^5.4.0
  cached_network_image: ^3.3.0
  video_player: ^2.8.0
  mobile_scanner: ^5.0.0
  shared_preferences: ^2.2.0
  multicast_dns: ^0.3.2
  path_provider: ^2.1.0
  permission_handler: ^11.0.0
  image_picker: ^1.0.0
  intl: ^0.19.0
```

- [ ] **Step 3: 创建 main.dart**

```dart
import 'package:flutter/material.dart';
import 'screens/connect_screen.dart';

void main() => runApp(const BlurArcApp());

class BlurArcApp extends StatelessWidget {
  const BlurArcApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Blur Arc',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF22D3EE),
          brightness: Brightness.dark,
        ),
      ),
      home: const ConnectScreen(),
    );
  }
}
```

- [ ] **Step 4: 创建 api_client.dart（Dio + token 注入）**

```dart
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static const String _tokenKey = 'mobile_token';
  static const String _hostKey = 'mobile_host';
  static const String _portKey = 'mobile_port';

  late final Dio _dio;
  String? _host;
  int? _port;
  String? _token;

  ApiClient() {
    _dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 5),
      receiveTimeout: const Duration(seconds: 10),
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_token != null) {
          options.headers['Authorization'] = 'Bearer $_token';
        }
        handler.next(options);
      },
      onError: (error, handler) {
        if (error.response?.statusCode == 401) {
          // Token invalid/revoked
          _token = null;
          _clearStored().then((_) {});
        }
        handler.next(error);
      },
    ));
  }

  String get baseUrl => 'http://$_host:$_port';

  Future<bool> loadFromStorage() async {
    final prefs = await SharedPreferences.getInstance();
    _host = prefs.getString(_hostKey);
    _port = prefs.getInt(_portKey);
    _token = prefs.getString(_tokenKey);
    return _host != null && _port != null && _token != null;
  }

  Future<void> saveConnection(String host, int port, String token) async {
    _host = host; _port = port; _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_hostKey, host);
    await prefs.setInt(_portKey, port);
    await prefs.setString(_tokenKey, token);
  }

  Future<void> _clearStored() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_hostKey);
    await prefs.remove(_portKey);
    await prefs.remove(_tokenKey);
  }

  Future<bool> verifyToken() async {
    try {
      final res = await _dio.get('$baseUrl/api/mobile/verify');
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Map> getTree() async {
    final res = await _dio.get('$baseUrl/api/mobile/tree');
    return res.data;
  }

  Future<Map> getPhotos(String path, {int page = 1, int pageSize = 100}) async {
    final res = await _dio.get('$baseUrl/api/mobile/photos',
      queryParameters: {'path': path, 'page': page, 'page_size': pageSize});
    return res.data;
  }

  String getThumbnailUrl(String path) =>
      '$baseUrl/api/mobile/thumbnail?path=${Uri.encodeComponent(path)}';

  String getFileUrl(String path) =>
      '$baseUrl/api/mobile/file?path=${Uri.encodeComponent(path)}';
}
```

- [ ] **Step 5: Create connect_screen.dart（QR 扫码 / 手动输入）**

连接页面有三种子状态：
1. **有已保存 token** → 尝试自动连接 → 成功则跳主页，失败则提示重新连接
2. **无 token** → 显示扫码界面 + 手动输入 IP 入口
3. **手动输入** → IP + 端口输入框 + 配对码输入框

- [ ] **Step 6: Verify Flutter project compiles**

```bash
cd "F:\AI\Frame_Album\blurarc_app" && flutter pub get && flutter analyze
```

Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add blurarc_app/
git commit -m "feat: initialize Flutter app with Dio client and connect screen (Phase 4)"
```

---

### Task 5: Flutter 相册浏览（手机/平板自适应）

**Files:**
- Create: `blurarc_app/lib/screens/album_screen.dart` — 相册首页
- Create: `blurarc_app/lib/screens/photo_grid_screen.dart` — 照片网格
- Create: `blurarc_app/lib/screens/photo_preview_screen.dart` — 全屏预览
- Create: `blurarc_app/lib/widgets/tree_view.dart` — 目录树
- Create: `blurarc_app/lib/widgets/photo_card.dart` — 照片卡片
- Create: `blurarc_app/lib/widgets/responsive_layout.dart` — 自适应布局
- Create: `blurarc_app/lib/models/album_tree.dart` — 数据模型
- Create: `blurarc_app/lib/models/photo.dart` — 照片模型

- [ ] **Step 1: Create data models**

`album_tree.dart`:
```dart
class TreeNode {
  final String name;
  final String path;
  final int count;
  final List<TreeNode> children;

  TreeNode({required this.name, required this.path, this.count = 0, this.children = const []});

  factory TreeNode.fromJson(Map<String, dynamic> json) => TreeNode(
    name: json['name'] ?? '',
    path: json['path'] ?? '',
    count: json['count'] ?? 0,
    children: (json['children'] as List? ?? []).map((c) => TreeNode.fromJson(c)).toList(),
  );

  bool get isYearMonth => name.length == 7 && name.contains('-');
}
```

`photo.dart`:
```dart
class Photo {
  final String id;
  final String name;
  final String path;
  final int size;
  final String date;
  final String type; // 'photo' | 'video'
  final String? duration;

  Photo({required this.id, required this.name, required this.path, required this.size, required this.date, required this.type, this.duration});

  factory Photo.fromJson(Map<String, dynamic> json) => Photo(
    id: json['id']?.toString() ?? '',
    name: json['name'] ?? '',
    path: json['path'] ?? '',
    size: json['size'] ?? 0,
    date: json['date'] ?? '',
    type: json['type'] ?? 'photo',
    duration: json['duration'],
  );

  bool get isVideo => type == 'video';
}
```

- [ ] **Step 2: Create album_screen.dart（自适应布局）**

核心布局逻辑：
```dart
class AlbumScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width > 600;
    // 宽屏（平板）→ 左侧目录树 + 右侧照片网格（分栏）
    // 窄屏（手机）→ 目录树列表 → 点击进入照片网格
    if (isWide) {
      return Row(
        children: [
          SizedBox(width: 280, child: TreeView(onSelect: _loadPhotos)),
          const VerticalDivider(width: 1),
          Expanded(child: PhotoGridScreen(path: _selectedPath)),
        ],
      );
    }
    // 手机：全屏目录树，点击后 push 到照片网格
    if (_selectedPath == null) {
      return TreeView(onSelect: (path) {
        Navigator.push(context, MaterialPageRoute(builder: (_) => PhotoGridScreen(path: path)));
      });
    }
    return PhotoGridScreen(path: _selectedPath);
  }
}
```

- [ ] **Step 3: Create photo_grid_screen.dart（GridView + 无限滚动）**

```dart
// 手机: 2-3 列, 平板: 4-6 列
final crossAxisCount = MediaQuery.of(context).size.width > 900 ? 6
    : MediaQuery.of(context).size.width > 600 ? 4 : 3;
```

使用 `cached_network_image` 显示缩略图，`ScrollController` 实现无限滚动加载更多。

- [ ] **Step 4: Create photo_preview_screen.dart（全屏预览）**

```dart
// 左右滑动 PageView
// 照片: Image.network (cached)
// 视频: video_player + VideoPlayerController.networkUrl
```

- [ ] **Step 5: Verify**

```bash
cd "F:\AI\Frame_Album\blurarc_app" && flutter analyze
```

Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add blurarc_app/
git commit -m "feat: add album browsing with phone/tablet responsive layout (Phase 5)"
```

---

### Task 6: Flutter 推送照片

**Files:**
- Create: `blurarc_app/lib/screens/upload_screen.dart`
- Create: `blurarc_app/lib/widgets/upload_progress.dart`

- [ ] **Step 1: Create upload_screen.dart**

使用 `image_picker` 插件访问系统相册，选择照片后通过 Dio 的 `MultipartFile` 逐个上传并显示进度。

```dart
// 选择照片
final images = await ImagePicker().pickMultiImage();

// 逐个上传
for (final img in images) {
  final bytes = await img.readAsBytes();
  final formData = FormData.fromMap({
    'file': MultipartFile.fromBytes(bytes, filename: img.name),
  });
  await _dio.post('$baseUrl/api/mobile/upload', data: formData,
    onSendProgress: (sent, total) {
      setState(() => _progress[s.name] = sent / total);
    },
  );
}
```

- [ ] **Step 2: Create upload_progress.dart**

水平进度条 + 文件列表（文件名 + 大小 + 状态图标），与网页版本类似。

- [ ] **Step 3: Verify**

```bash
cd "F:\AI\Frame_Album\blurarc_app" && flutter analyze
```

- [ ] **Step 4: Commit**

```bash
git add blurarc_app/
git commit -m "feat: add photo upload screen with progress tracking (Phase 6)"
```

---

### Task 7: 联调 + 端到端验证

- [ ] **Step 1: 启动电脑端移动接入服务**

```bash
cd "F:\AI\Frame_Album" && cd frontend && npm run build && cd .. && python src/BlurArc.py
```

- [ ] **Step 2: 启动 Flutter App**

```bash
cd "F:\AI\Frame_Album\blurarc_app" && flutter run
```

（需要连接安卓真机或模拟器）

- [ ] **Step 3: 验证完整流程**

1. 电脑端点击 📱 按钮 → 开启移动接入服务 → 显示二维码
2. Flutter App 扫码 → 电脑端弹配对确认 → 点「允许」
3. App 进入相册 → 按年月浏览 → 点击查看照片
4. 在 App 上推送照片 → 电脑端收到通知 → 确认导入

- [ ] **Step 4: 提交最终调整**

```bash
git add -A && git commit -m "feat: end-to-end mobile access with Flutter app"
```
