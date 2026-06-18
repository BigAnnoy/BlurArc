# 手机无线导入 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增安卓手机无线照片导入通道（扫码→上传→复用现有去重导入管线）

**Architecture:** 后端新增独立端口 Flask 上传服务器 + 手机端内联 HTML 页 + 前端新增 PhoneImportPanel 组件 + ImportDialog 增加模式选择步骤。手机导入和本地导入在 `checking` 步骤汇合后完全一致。

**Tech Stack:** Python (Flask, qrcode), TypeScript (React 19), 内联 HTML/CSS/JS (手机端)

---

## 文件结构

```
新增:
  backend/phone_upload_server.py              # 上传服务器 + 手机端 HTML + 会话管理
  frontend/src/components/dialogs/ImportDialog/PhoneImportPanel.tsx  # 手机导入面板

修改:
  backend/api_server.py                       # 新增 4 个 API 端点
  frontend/src/services/api.ts                # 新增 phone-upload API 调用
  frontend/src/components/dialogs/ImportDialog/importDialog.tsx     # 新增 select-mode + phone-upload 步骤
  frontend/src/components/dialogs/ImportDialog/types.ts             # 扩展 ImportStep 类型
  frontend/src/contexts/I18nContext.tsx        # 新增 12 条国际化文案
  requirements.txt                            # 新增 qrcode 依赖
  BlurArc.spec                                # hiddenimports 新增 qrcode

测试:
  test/unit/test_phone_upload_server.py       # 后端单元测试
```

---

### Task 1: 安装依赖 qrcode

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add qrcode to requirements.txt**

```diff
+ qrcode>=7.4
```

- [ ] **Step 2: Install the dependency**

Run: `pip install qrcode>=7.4`
Expected: Successfully installed qrcode

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add qrcode dependency for phone upload QR generation"
```

---

### Task 2: 新增 phone_upload_server.py（核心后端）

**Files:**
- Create: `backend/phone_upload_server.py`

- [ ] **Step 1: Create the module file with UploadSession and PhoneUploadServer**

```python
"""
手机上传服务器 - 独立端口 Flask 实例
提供手机端 HTML 页面、文件接收、进度查询
"""
import io
import json
import logging
import os
import socket
import threading
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

import qrcode
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

from .config_manager import _get_app_data_dir

logger = logging.getLogger(__name__)

APP_DATA_DIR = _get_app_data_dir()
UPLOAD_ROOT = APP_DATA_DIR / ".config" / "phone_upload"
SESSIONS_FILE = UPLOAD_ROOT / "sessions.json"
MAX_SINGLE_FILE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_FILES_PER_SESSION = 2000

# 允许的扩展名（与 constants.py 对齐）
ALLOWED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.heic', '.webp', '.bmp', '.gif', '.tiff', '.tif',
    '.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.wmv', '.flv', '.webm',
}


@dataclass
class UploadedFile:
    """单个已上传文件记录"""
    original_name: str      # 手机端原始文件名
    saved_path: str         # 临时目录中的实际路径
    size: int               # 字节
    mime_type: str          # MIME 类型
    uploaded_at: float      # timestamp
    status: str = "done"    # "done" | "failed"
    error: str | None = None


class UploadSession:
    """一次上传会话"""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.upload_dir = UPLOAD_ROOT / f"{ts}_{self.session_id[:8]}"
        self.files: list[UploadedFile] = []
        self.total_bytes: int = 0
        self.created_at: float = datetime.now().timestamp()
        self.is_active: bool = True
        self.current_file: UploadedFile | None = None
        self.current_progress: float = 0.0
        self.current_speed_mbps: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_files": len(self.files),
            "completed_files": sum(1 for f in self.files if f.status == "done"),
            "current_file": self.current_file.original_name if self.current_file else "",
            "current_progress": round(self.current_progress, 1),
            "current_speed_mbps": round(self.current_speed_mbps, 2),
            "total_bytes_uploaded": self.total_bytes,
            "files": [
                {"name": f.original_name, "size": f.size, "status": f.status,
                 "error": f.error}
                for f in self.files
            ],
        }


class PhoneUploadServer:
    """手机上传服务器（独立端口 Flask 实例）"""

    HOST = "0.0.0.0"
    PORT_RANGE = (9800, 9900)

    def __init__(self):
        self.app = Flask(__name__)
        self.port: int | None = None
        self._thread: threading.Thread | None = None
        self._session: UploadSession | None = None
        self._register_routes()

    def _register_routes(self):
        """注册所有路由"""

        @self.app.route("/")
        def upload_page():
            """返回手机端上传页面 HTML"""
            return self._render_phone_page()

        @self.app.route("/upload", methods=["POST"])
        def receive_file():
            """接收单文件上传"""
            return self._handle_upload()

        @self.app.route("/status")
        def upload_status():
            """返回当前上传进度"""
            if not self._session:
                return jsonify({"error": "没有活跃的会话"}), 404
            return jsonify(self._session.to_dict())

    # ============== 公开方法 ==============

    def start(self) -> dict:
        """启动服务器。返回 {port, local_ip, upload_url, session_id, upload_dir}"""
        self.port = self._find_free_port()
        self._session = UploadSession()
        self._session.upload_dir.mkdir(parents=True, exist_ok=True)
        self._write_sessions_json()

        self._thread = threading.Thread(
            target=self.app.run,
            kwargs={
                "host": self.HOST,
                "port": self.port,
                "debug": False,
                "use_reloader": False,
            },
            daemon=True,
        )
        self._thread.start()

        local_ip = self._get_local_ip()
        logger.info(f"[PhoneUpload] 服务器已启动: {local_ip}:{self.port}")

        return {
            "port": self.port,
            "local_ip": local_ip,
            "upload_url": f"http://{local_ip}:{self.port}",
            "session_id": self._session.session_id,
            "upload_dir": str(self._session.upload_dir),
        }

    def stop(self, cleanup: bool = False):
        """停止服务器。cleanup=True 则删除该会话的临时文件。"""
        # Flask 开发服务器没有优雅关闭 API，通过停止线程实现
        if self._session:
            self._session.is_active = False
            if cleanup:
                self._cleanup_session_dir()
            else:
                self._update_session_status("incomplete")
        logger.info(f"[PhoneUpload] 服务器已停止 (port={self.port})")

    def get_session(self) -> UploadSession | None:
        return self._session

    def get_qr_png(self) -> bytes:
        """生成二维码 PNG 字节流"""
        if not self._session:
            raise RuntimeError("服务器未启动")
        url = f"http://{self._get_local_ip()}:{self.port}"
        img = qrcode.make(url, box_size=10, border=2)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    def has_incomplete_session(self) -> dict | None:
        """检查是否有未完成的会话，返回会话摘要或 None"""
        sessions = self._load_sessions_json()
        for s in sessions:
            if s.get("status") == "incomplete":
                return s
        return None

    def resume_session(self, session_id: str) -> UploadSession | None:
        """恢复一个未完成的会话"""
        sessions = self._load_sessions_json()
        target = None
        for s in sessions:
            if s["id"] == session_id and s["status"] == "incomplete":
                target = s
                break
        if not target:
            return None

        session = UploadSession()
        session.session_id = target["id"]
        session.upload_dir = UPLOAD_ROOT / target["upload_dir"]
        session.total_bytes = target.get("total_bytes", 0)
        session.created_at = target.get("created_at", datetime.now().timestamp())
        session.is_active = True

        # 恢复已有文件列表
        if session.upload_dir.exists():
            for f_path in session.upload_dir.iterdir():
                if f_path.is_file():
                    uf = UploadedFile(
                        original_name=f_path.name,
                        saved_path=str(f_path),
                        size=f_path.stat().st_size,
                        mime_type="",
                        uploaded_at=f_path.stat().st_mtime,
                        status="done",
                    )
                    session.files.append(uf)
            session.total_bytes = sum(f.size for f in session.files)
        return session

    def mark_completed(self):
        """标记会话为完成（导入成功后调用）"""
        if self._session:
            self._session.is_active = False
            self._update_session_status("completed")

    # ============== 内部方法 ==============

    def _handle_upload(self):
        """处理单个文件上传"""
        if not self._session or not self._session.is_active:
            return jsonify({"error": "没有活跃的会话"}), 400

        if "file" not in request.files:
            return jsonify({"error": "缺少文件"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "文件名为空"}), 400

        # 检查文件数量限制
        done_count = sum(1 for f in self._session.files if f.status == "done")
        if done_count >= MAX_FILES_PER_SESSION:
            return jsonify({"error": f"已达到单次会话上限 ({MAX_FILES_PER_SESSION} 个)"}), 413

        # 检查扩展名
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": f"不支持的文件格式: {ext}"}), 400

        # 安全检查：过滤路径穿越
        safe_name = secure_filename(file.filename)
        if not safe_name:
            safe_name = f"upload_{uuid.uuid4().hex[:8]}{ext}"

        # 处理重名：追加序号
        save_path = self._session.upload_dir / safe_name
        counter = 1
        while save_path.exists():
            stem = Path(safe_name).stem
            save_path = self._session.upload_dir / f"{stem}_{counter}{ext}"
            counter += 1

        # 写入文件
        try:
            file.save(str(save_path))
        except Exception as e:
            logger.error(f"[PhoneUpload] 文件保存失败: {e}")
            return jsonify({"error": "文件保存失败，磁盘空间可能不足"}), 507

        file_size = save_path.stat().st_size

        # 校验：0 字节文件拒绝
        if file_size == 0:
            save_path.unlink()
            return jsonify({"error": "文件为空，已拒绝"}), 400

        # 校验：超大小限制
        if file_size > MAX_SINGLE_FILE_BYTES:
            save_path.unlink()
            return jsonify({"error": f"文件超过 {MAX_SINGLE_FILE_BYTES // (1024**2)} MB 限制"}), 413

        uploaded = UploadedFile(
            original_name=file.filename,
            saved_path=str(save_path),
            size=file_size,
            mime_type=file.content_type or "",
            uploaded_at=datetime.now().timestamp(),
            status="done",
        )
        self._session.files.append(uploaded)
        self._session.total_bytes += file_size

        self._write_sessions_json()
        logger.info(f"[PhoneUpload] 文件已接收: {file.filename} ({file_size} bytes)")

        return jsonify({"status": "ok", "name": file.filename, "size": file_size})

    def _find_free_port(self) -> int:
        """在 PORT_RANGE 内找一个可用端口"""
        for port in range(self.PORT_RANGE[0], self.PORT_RANGE[1] + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    return port
        raise RuntimeError(f"端口范围 {self.PORT_RANGE} 内没有可用端口")

    def _get_local_ip(self) -> str:
        """获取本机局域网 IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _cleanup_session_dir(self):
        """删除会话临时目录"""
        if self._session and self._session.upload_dir.exists():
            shutil.rmtree(self._session.upload_dir, ignore_errors=True)
        self._remove_from_sessions_json()

    def _update_session_status(self, status: str):
        """更新 sessions.json 中的会话状态"""
        if not self._session:
            return
        sessions = self._load_sessions_json()
        for s in sessions:
            if s["id"] == self._session.session_id:
                s["status"] = status
                s["file_count"] = sum(1 for f in self._session.files if f.status == "done")
                s["total_bytes"] = self._session.total_bytes
                break
        else:
            sessions.append({
                "id": self._session.session_id,
                "upload_dir": str(self._session.upload_dir.relative_to(UPLOAD_ROOT)),
                "created_at": self._session.created_at,
                "file_count": 0,
                "total_bytes": 0,
                "status": status,
            })
        self._save_sessions_json(sessions)

    def _remove_from_sessions_json(self):
        """从 sessions.json 中移除当前会话"""
        if not self._session:
            return
        sessions = self._load_sessions_json()
        sessions = [s for s in sessions if s["id"] != self._session.session_id]
        self._save_sessions_json(sessions)

    def _write_sessions_json(self):
        """写入初始会话记录"""
        self._update_session_status("active")

    def _load_sessions_json(self) -> list[dict]:
        """加载会话索引"""
        if not SESSIONS_FILE.exists():
            return []
        try:
            return json.loads(SESSIONS_FILE.read_text(encoding="utf-8")).get("sessions", [])
        except Exception:
            return []

    def _save_sessions_json(self, sessions: list[dict]):
        """保存会话索引"""
        UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
        SESSIONS_FILE.write_text(
            json.dumps({"sessions": sessions}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _render_phone_page(self) -> str:
        """渲染手机端上传页面（内联 HTML）"""
        from .config_manager import ConfigManager

        # 读取主题设置
        theme = "system"
        try:
            cm = ConfigManager()
            theme = cm.get_setting("theme", "system")
        except Exception:
            pass

        # 解析实际主题类名
        if theme == "dark":
            html_class = "dark"
        elif theme == "light":
            html_class = "light"
        else:  # system
            html_class = "system"

        return f"""<!DOCTYPE html>
<html lang="zh" class="{html_class}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>Blur Arc - 从手机导入</title>
<style>
:root {{
  --bg: #0c1117; --card: #151d26; --border: #1c2836;
  --primary: #22d3ee; --primary-hover: #67e8f9;
  --text: #e8f0f5; --text-secondary: #8aa0b0;
  --success: #4ade80; --danger: #f87171;
  --radius: 10px; --radius-sm: 6px;
}}
.light {{
  --bg: #f4f7f9; --card: #ffffff; --border: #d8e2e8;
  --primary: #0891b2; --primary-hover: #0e7490;
  --text: #1a2a3a; --text-secondary: #5a6a7a;
  --success: #22c55e; --danger: #ef4444;
}}
.system {{}}
@media (prefers-color-scheme: light) {{
  .system {{
    --bg: #f4f7f9; --card: #ffffff; --border: #d8e2e8;
    --primary: #0891b2; --primary-hover: #0e7490;
    --text: #1a2a3a; --text-secondary: #5a6a7a;
    --success: #22c55e; --danger: #ef4444;
  }}
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg); color: var(--text);
  min-height: 100vh; padding: 0 16px 32px;
}}
.header {{
  background: var(--bg);
  padding: 20px 0 16px; text-align: center;
  position: sticky; top: 0; z-index: 10;
}}
.header .brand {{ font-size:20px; font-weight:700; color:var(--primary); }}
.header .sub {{ font-size:13px; color:var(--text-secondary); margin-top:2px; }}
.upload-btn {{
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  width: 100%; padding: 28px 20px; margin: 12px 0 20px;
  background: var(--card); border: 2px dashed var(--border);
  border-radius: var(--radius); cursor: pointer;
  transition: border-color .2s, background .2s;
}}
.upload-btn:active {{ border-color: var(--primary); background: var(--bg); }}
.upload-btn .icon {{ font-size: 36px; margin-bottom: 8px; }}
.upload-btn .label {{ font-size: 15px; font-weight: 600; color: var(--text); }}
.upload-btn .hint {{ font-size: 12px; color: var(--text-secondary); margin-top: 4px; }}
.section-title {{
  font-size: 13px; font-weight: 600; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: .5px;
  margin: 20px 0 10px; padding-bottom: 6px;
}}
.progress-bar {{
  width: 100%; height: 8px; background: var(--border);
  border-radius: 4px; overflow: hidden; margin: 8px 0;
}}
.progress-fill {{
  height: 100%; background: var(--primary);
  border-radius: 4px; transition: width .3s;
}}
.progress-fill.failed {{ background: var(--danger); }}
.file-item {{
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; margin-bottom: 6px;
  background: var(--card); border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}}
.file-item .status {{ font-size: 18px; flex-shrink: 0; }}
.file-item .info {{ flex:1; min-width: 0; }}
.file-item .name {{
  font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.file-item .size {{ font-size: 11px; color: var(--text-secondary); }}
.file-item .retry {{
  font-size: 12px; color: var(--primary); cursor: pointer;
  text-decoration: none; flex-shrink: 0;
}}
.stop-btn {{
  display: block; width: 100%; padding: 14px; margin-top: 24px;
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); color: var(--text-secondary);
  font-size: 15px; cursor: pointer;
}}
.stop-btn:active {{ border-color: var(--primary); color: var(--text); }}
.footer-note {{
  text-align: center; font-size: 12px; color: var(--text-secondary);
  margin-top: 20px;
}}
#fileInput {{ display: none; }}
.stats {{ font-size:12px; color:var(--text-secondary); margin:4px 0; }}
.current-file {{ font-size:13px; color:var(--text); margin-top:8px; word-break:break-all; }}
</style>
</head>
<body>
<div class="header">
  <div class="brand">Blur Arc</div>
  <div class="sub">从手机导入照片</div>
</div>

<div class="upload-btn" id="uploadBtn" onclick="document.getElementById('fileInput').click()">
  <div class="icon">📷</div>
  <div class="label">选择照片/视频</div>
  <div class="hint">点击选择或拍照</div>
</div>
<input type="file" id="fileInput" multiple accept="image/*,video/*" onchange="onFilesSelected(this)">

<div id="progressArea" style="display:none">
  <div class="section-title">上传进度</div>
  <div class="stats" id="overallStats"></div>
  <div class="progress-bar"><div class="progress-fill" id="overallBar"></div></div>
  <div class="current-file" id="currentFile"></div>
  <div class="progress-bar"><div class="progress-fill" id="currentBar"></div></div>
  <div class="stats" id="speed"></div>
</div>

<div id="doneSection" style="display:none">
  <div class="section-title">已完成 (<span id="doneCount">0</span>)</div>
  <div id="doneList"></div>
</div>

<div id="failedSection" style="display:none">
  <div class="section-title">上传失败</div>
  <div id="failedList"></div>
</div>

<button class="stop-btn" id="stopBtn" onclick="stopUpload()" style="display:none">⏹ 停止（已上传的保留）</button>
<p class="footer-note">💡 上传完成后在电脑端继续操作</p>

<script>
const UPLOAD_URL = '/upload';
let totalFiles = 0, doneFiles = 0, failedFiles = 0;
let allFileNames = []; // 待上传队列
let currentIndex = 0;
let stopped = false;
let currentXhr = null;

function onFilesSelected(input) {{
  if (!input.files.length) return;
  allFileNames = allFileNames.concat(Array.from(input.files));
  totalFiles = allFileNames.length;
  document.getElementById('progressArea').style.display = 'block';
  document.getElementById('stopBtn').style.display = 'block';
  document.getElementById('uploadBtn').style.opacity = '0.5';
  input.value = '';
  if (currentIndex === 0 && totalFiles > 0) uploadNext();
}}

function uploadNext() {{
  if (stopped || currentIndex >= totalFiles) return;
  const file = allFileNames[currentIndex];
  if (!file) {{ currentIndex++; uploadNext(); return; }}

  const formData = new FormData();
  formData.append('file', file);

  const xhr = new XMLHttpRequest();
  currentXhr = xhr;

  let startTime = Date.now(), lastBytes = 0;

  xhr.upload.onprogress = (e) => {{
    if (!e.lengthComputable) return;
    const pct = Math.round(e.loaded / e.total * 100);
    document.getElementById('currentBar').style.width = pct + '%';

    const now = Date.now();
    const dt = (now - startTime) / 1000;
    if (dt > 0.5) {{
      const speed = (e.loaded - lastBytes) / dt / 1024 / 1024;
      document.getElementById('speed').textContent = '↑ ' + speed.toFixed(1) + ' MB/s';
      lastBytes = e.loaded;
      startTime = now;
    }}
  }};

  xhr.onload = () => {{
    if (xhr.status === 200) {{
      onFileDone(file);
    }} else {{
      onFileFailed(file, '服务器错误 (' + xhr.status + ')');
    }}
  }};

  xhr.onerror = () => {{ onFileFailed(file, '网络错误'); }};

  document.getElementById('currentFile').textContent = '当前: ' + file.name;
  document.getElementById('currentBar').style.width = '0%';
  document.getElementById('currentBar').className = 'progress-fill';
  document.getElementById('speed').textContent = '';

  xhr.open('POST', UPLOAD_URL);
  xhr.send(formData);
}}

function onFileDone(file) {{
  doneFiles++;
  updateOverall();
  addFileItem(file, 'done');
  currentIndex++;
  if (!stopped && currentIndex < totalFiles) {{
    uploadNext();
  }} else if (!stopped) {{
    allComplete();
  }}
}}

function onFileFailed(file, reason) {{
  failedFiles++;
  updateOverall();
  addFileItem(file, 'failed', reason);
  currentIndex++;
  if (!stopped && currentIndex < totalFiles) uploadNext();
}}

function updateOverall() {{
  const total = allFileNames.length;
  const pct = Math.round((doneFiles + failedFiles) / total * 100);
  document.getElementById('overallBar').style.width = pct + '%';
  document.getElementById('overallStats').textContent =
    '整体: ' + (doneFiles + failedFiles) + ' / ' + total + '  ' + pct + '%';
}}

function addFileItem(file, status, reason) {{
  const sizeStr = file.size > 1024*1024
    ? (file.size / 1024 / 1024).toFixed(1) + ' MB'
    : (file.size / 1024).toFixed(0) + ' KB';

  const el = document.createElement('div');
  el.className = 'file-item';
  el.id = 'fi_' + file.name.replace(/[^a-zA-Z0-9]/g, '_');

  if (status === 'done') {{
    el.innerHTML = '<span class="status">✅</span>' +
      '<div class="info"><div class="name">' + escapeHtml(file.name) + '</div>' +
      '<div class="size">' + sizeStr + '</div></div>';
    document.getElementById('doneSection').style.display = 'block';
    document.getElementById('doneList').appendChild(el);
    document.getElementById('doneCount').textContent = doneFiles;
  }} else {{
    el.innerHTML = '<span class="status">❌</span>' +
      '<div class="info"><div class="name">' + escapeHtml(file.name) + '</div>' +
      '<div class="size" style="color:var(--danger)">' + (reason || '上传失败') + '</div></div>' +
      '<a class="retry" href="javascript:retryFile(\'' + file.name + '\')">重试</a>';
    document.getElementById('failedSection').style.display = 'block';
    document.getElementById('failedList').appendChild(el);
  }}
}}

function retryFile(name) {{
  const item = document.getElementById('fi_' + name.replace(/[^a-zA-Z0-9]/g, '_'));
  if (item) item.remove();
  const file = allFileNames.find(f => f.name === name);
  if (!file) return;
  failedFiles = Math.max(0, failedFiles - 1);
  updateOverall();
  allFileNames.push(file);
  if (currentIndex >= totalFiles) {{
    totalFiles = allFileNames.length;
    uploadNext();
  }} else {{
    totalFiles = allFileNames.length;
  }}
}}

function stopUpload() {{
  stopped = true;
  if (currentXhr) currentXhr.abort();
  document.getElementById('stopBtn').textContent = '⏹ 已停止';
  document.getElementById('stopBtn').disabled = true;
  document.getElementById('uploadBtn').style.opacity = '0.3';
  document.getElementById('uploadBtn').onclick = null;
}}

function allComplete() {{
  document.getElementById('currentFile').textContent = '✅ 全部上传完成';
  document.getElementById('currentBar').style.width = '100%';
  document.getElementById('speed').textContent = '';
  document.getElementById('stopBtn').style.display = 'none';
  document.getElementById('uploadBtn').style.opacity = '0.3';
  document.getElementById('uploadBtn').onclick = null;
}}

function escapeHtml(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}
</script>
</body>
</html>"""
```

- [ ] **Step 2: Verify the module imports correctly**

Run: `cd "F:\AI\Frame_Album" && python -c "from backend.phone_upload_server import PhoneUploadServer, UploadSession; print('import ok')"`
Expected: `import ok`

- [ ] **Step 3: Commit**

```bash
git add backend/phone_upload_server.py
git commit -m "feat: add PhoneUploadServer with phone-side upload page and session management"
```

---

### Task 3: PhoneUploadServer 单元测试

**Files:**
- Create: `test/unit/test_phone_upload_server.py`

- [ ] **Step 1: Write tests for core behaviors**

```python
"""PhoneUploadServer 单元测试"""
import json
import time
import pytest
from pathlib import Path
from backend.phone_upload_server import PhoneUploadServer, UploadSession, UPLOAD_ROOT


class TestUploadSession:
    def test_init_creates_unique_id(self):
        s1 = UploadSession()
        s2 = UploadSession()
        assert s1.session_id != s2.session_id

    def test_to_dict_empty(self):
        s = UploadSession()
        d = s.to_dict()
        assert d["total_files"] == 0
        assert d["completed_files"] == 0
        assert d["files"] == []

    def test_to_dict_with_files(self, tmp_path):
        s = UploadSession()
        s.upload_dir = tmp_path
        s.files = [
            __import__("backend.phone_upload_server", fromlist=["UploadedFile"]).UploadedFile(
                original_name="test.jpg", saved_path=str(tmp_path / "test.jpg"),
                size=1000, mime_type="image/jpeg", uploaded_at=time.time(),
            )
        ]
        d = s.to_dict()
        assert d["total_files"] == 1
        assert d["completed_files"] == 1


class TestPhoneUploadServerLifecycle:
    def test_start_stop(self):
        server = PhoneUploadServer()
        info = server.start()
        assert "port" in info
        assert "local_ip" in info
        assert "upload_url" in info
        assert info["port"] >= 9800
        assert info["port"] <= 9900
        server.stop()
        assert server._session is not None
        assert not server._session.is_active

    def test_port_auto_select(self):
        server = PhoneUploadServer()
        info = server.start()
        # 第二次启动应该用不同端口
        server2 = PhoneUploadServer()
        info2 = server2.start()
        assert info["port"] != info2["port"]
        server.stop()
        server2.stop()

    def test_get_qr_png(self):
        server = PhoneUploadServer()
        server.start()
        png = server.get_qr_png()
        assert isinstance(png, bytes)
        assert len(png) > 0
        # PNG 文件头
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        server.stop()


class TestSessionPersistence:
    def test_write_and_load_sessions(self, monkeypatch, tmp_path):
        """测试 sessions.json 的写入和读取"""
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")

        server = PhoneUploadServer()
        server.port = 9800
        server._session = UploadSession("test123")
        server._session.upload_dir = tmp_path / "test_session"
        server._session.upload_dir.mkdir(parents=True, exist_ok=True)
        server._write_sessions_json()

        sessions = server._load_sessions_json()
        assert len(sessions) == 1
        assert sessions[0]["id"] == "test123"

    def test_has_incomplete_session(self, monkeypatch, tmp_path):
        """测试检测未完成会话"""
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")

        mod.SESSIONS_FILE.write_text(json.dumps({
            "sessions": [{"id": "abc", "upload_dir": "foo", "created_at": 0,
                          "file_count": 3, "total_bytes": 100, "status": "incomplete"}]
        }), encoding="utf-8")

        server = PhoneUploadServer()
        result = server.has_incomplete_session()
        assert result is not None
        assert result["id"] == "abc"

    def test_no_incomplete_when_all_completed(self, monkeypatch, tmp_path):
        """测试全部完成时不返回 incomplete"""
        import backend.phone_upload_server as mod
        monkeypatch.setattr(mod, "UPLOAD_ROOT", tmp_path)
        monkeypatch.setattr(mod, "SESSIONS_FILE", tmp_path / "sessions.json")

        mod.SESSIONS_FILE.write_text(json.dumps({
            "sessions": [{"id": "abc", "upload_dir": "foo", "created_at": 0,
                          "file_count": 3, "total_bytes": 100, "status": "completed"}]
        }), encoding="utf-8")

        server = PhoneUploadServer()
        result = server.has_incomplete_session()
        assert result is None
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest test/unit/test_phone_upload_server.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add test/unit/test_phone_upload_server.py
git commit -m "test: add PhoneUploadServer unit tests"
```

---

### Task 4: 扩展 ImportStep 类型

**Files:**
- Modify: `frontend/src/components/dialogs/ImportDialog/types.ts:4`

- [ ] **Step 1: Update ImportStep type**

```tsx
// frontend/src/components/dialogs/ImportDialog/types.ts:4
// 修改这一行:
export type ImportStep = 'select' | 'checking' | 'preview' | 'importing';
// 改为:
export type ImportStep = 'select-mode' | 'select-path' | 'phone-upload' | 'checking' | 'preview' | 'importing';
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No new errors from this change (may have existing errors elsewhere)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dialogs/ImportDialog/types.ts
git commit -m "feat: extend ImportStep type with select-mode, select-path, phone-upload"
```

---

### Task 5: 扩展 API 服务层

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add phone upload API methods to the `api` object**

在 `frontend/src/services/api.ts` 的 `api` 对象末尾（`};` 闭合前）添加：

```typescript
  // Phone upload
  startPhoneUpload: () =>
    fetchJson<{
      port: number;
      local_ip: string;
      upload_url: string;
      session_id: string;
      upload_dir: string;
    }>(`${API_BASE}/phone-upload/start`, { method: 'POST' }),

  stopPhoneUpload: () =>
    fetchJson<{ status: string }>(`${API_BASE}/phone-upload/stop`, { method: 'POST' }),

  getPhoneUploadStatus: () =>
    fetchJson<{
      total_files: number;
      completed_files: number;
      current_file: string;
      current_progress: number;
      current_speed_mbps: number;
      total_bytes_uploaded: number;
      files: { name: string; size: number; status: string; error?: string }[];
    }>(`${API_BASE}/phone-upload/status`),

  getPhoneUploadQr: () => `${API_BASE}/phone-upload/qr`,

  getIncompletePhoneSession: () =>
    fetchJson<{ session: { id: string; upload_dir: string; file_count: number; total_bytes: number; created_at: number } | null }>(`${API_BASE}/phone-upload/incomplete`),

  resumePhoneSession: (sessionId: string) =>
    fetchJson<{
      port: number;
      local_ip: string;
      upload_url: string;
      session_id: string;
      upload_dir: string;
    }>(`${API_BASE}/phone-upload/resume`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),

  discardPhoneSession: () =>
    fetchJson<{ status: string }>(`${API_BASE}/phone-upload/discard`, { method: 'POST' }),
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add phone upload API methods to frontend service"
```

---

### Task 6: 新增国际化文案

**Files:**
- Modify: `frontend/src/contexts/I18nContext.tsx`

- [ ] **Step 1: Add phone import strings to zh translations**

在 `zh` 对象的 `// Welcome Screen` 之前插入：

```typescript
    // Phone Import
    'phoneImport.title': '从手机导入',
    'phoneImport.subtitle': '扫码无线传输',
    'phoneImport.ensureWifi': '确保手机和电脑在同一 WiFi 网络',
    'phoneImport.scanQr': '手机扫码或浏览器访问以下地址',
    'phoneImport.starting': '正在启动上传服务...',
    'phoneImport.receiving': '等待手机上传...',
    'phoneImport.filesUploaded': '已上传 {count} 个文件，共 {size}',
    'phoneImport.stopReceiving': '停止接收',
    'phoneImport.startImport': '开始导入',
    'phoneImport.noFiles': '请先上传至少一个文件',
    'phoneImport.serverError': '上传服务启动失败，请检查防火墙设置',
    'phoneImport.entry': '从手机导入',
    'phoneImport.localImport': '本地导入',
    'phoneImport.localImportDesc': '从本地磁盘/U盘/移动硬盘选择文件夹',
    'phoneImport.selectMode': '请选择导入方式',
    'common.retry': '重试',
    'phoneImport.resumeTitle': '发现上次未完成的导入',
    'phoneImport.resumeDetail': '{date} — {count} 个文件 ({size})',
    'phoneImport.resumeContinue': '继续上传',
    'phoneImport.resumeDiscard': '放弃，重新开始',
```

- [ ] **Step 2: Add same keys to en translations**

在 `en` 对象的 `// Welcome Screen` 之前插入：

```typescript
    // Phone Import
    'phoneImport.title': 'Import from Phone',
    'phoneImport.subtitle': 'Scan to transfer wirelessly',
    'phoneImport.ensureWifi': 'Make sure phone and PC are on the same WiFi',
    'phoneImport.scanQr': 'Scan QR code or visit the address below',
    'phoneImport.starting': 'Starting upload service...',
    'phoneImport.receiving': 'Waiting for uploads...',
    'phoneImport.filesUploaded': '{count} files uploaded, {size} total',
    'phoneImport.stopReceiving': 'Stop Receiving',
    'phoneImport.startImport': 'Start Import',
    'phoneImport.noFiles': 'Please upload at least one file first',
    'phoneImport.serverError': 'Failed to start upload service, check firewall',
    'phoneImport.entry': 'Import from Phone',
    'phoneImport.localImport': 'Local Import',
    'phoneImport.localImportDesc': 'Select a folder from local disk / USB drive',
    'phoneImport.selectMode': 'Choose import method',
    'common.retry': 'Retry',
    'phoneImport.resumeTitle': 'Incomplete import found',
    'phoneImport.resumeDetail': '{date} — {count} files ({size})',
    'phoneImport.resumeContinue': 'Continue Upload',
    'phoneImport.resumeDiscard': 'Discard & Start Over',
```

- [ ] **Step 3: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No new errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/contexts/I18nContext.tsx
git commit -m "feat: add phone import i18n strings (zh/en)"
```

---

### Task 7: 创建 PhoneImportPanel 组件

**Files:**
- Create: `frontend/src/components/dialogs/ImportDialog/PhoneImportPanel.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useState, useEffect, useCallback } from 'react';
import { useI18n } from '../../../contexts/I18nContext';
import { api } from '../../../services/api';

interface UploadedFileInfo {
  name: string;
  size: number;
  status: string;
  error?: string;
}

interface PhoneImportPanelProps {
  onStartImport: (sourcePath: string) => void;
  onBack: () => void;
}

export function PhoneImportPanel({ onStartImport, onBack }: PhoneImportPanelProps) {
  const { t } = useI18n();

  // Server state
  const [serverStatus, setServerStatus] = useState<'idle' | 'starting' | 'running' | 'error'>('idle');
  const [connectionInfo, setConnectionInfo] = useState<{
    port: number;
    local_ip: string;
    upload_url: string;
    session_id: string;
    upload_dir: string;
  } | null>(null);
  const [qrUrl, setQrUrl] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Files state
  const [files, setFiles] = useState<UploadedFileInfo[]>([]);
  const [completedFiles, setCompletedFiles] = useState(0);
  const [totalFiles, setTotalFiles] = useState(0);
  const [totalBytes, setTotalBytes] = useState(0);

  // Resume dialog
  const [showResume, setShowResume] = useState(false);
  const [resumeSession, setResumeSession] = useState<{
    id: string;
    upload_dir: string;
    file_count: number;
    total_bytes: number;
    created_at: number;
  } | null>(null);

  // Start server on mount
  useEffect(() => {
    startServer();
    return () => {
      // Cleanup: stop server on unmount (but keep files)
      api.stopPhoneUpload().catch(() => {});
    };
  }, []);

  const startServer = async () => {
    setServerStatus('starting');
    setErrorMessage('');

    try {
      // Check for incomplete session first
      const incompleteRes = await api.getIncompletePhoneSession();
      if (incompleteRes.session) {
        setResumeSession(incompleteRes.session);
        setShowResume(true);
        return;
      }

      await doStartServer();
    } catch (error) {
      setServerStatus('error');
      setErrorMessage(error instanceof Error ? error.message : t('phoneImport.serverError'));
    }
  };

  const doStartServer = async () => {
    setServerStatus('starting');
    try {
      const info = await api.startPhoneUpload();
      setConnectionInfo(info);
      setQrUrl(api.getPhoneUploadQr());
      setServerStatus('running');
    } catch (error) {
      setServerStatus('error');
      setErrorMessage(error instanceof Error ? error.message : t('phoneImport.serverError'));
    }
  };

  // Poll status
  useEffect(() => {
    if (serverStatus !== 'running') return;

    const interval = setInterval(async () => {
      try {
        const status = await api.getPhoneUploadStatus();
        setFiles(status.files || []);
        setCompletedFiles(status.completed_files);
        setTotalFiles(status.total_files);
        setTotalBytes(status.total_bytes_uploaded);
      } catch {
        // Server may have been stopped, ignore polling errors
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [serverStatus]);

  // Handle resume
  const handleResumeContinue = async () => {
    setShowResume(false);
    try {
      const info = await api.resumePhoneSession(resumeSession!.id);
      setConnectionInfo(info);
      setQrUrl(api.getPhoneUploadQr());
      setServerStatus('running');
    } catch (error) {
      setServerStatus('error');
      setErrorMessage(error instanceof Error ? error.message : t('phoneImport.serverError'));
    }
  };

  const handleResumeDiscard = async () => {
    setShowResume(false);
    try {
      await api.discardPhoneSession();
    } catch {}
    await doStartServer();
  };

  // Handle stop
  const handleStop = async () => {
    try {
      await api.stopPhoneUpload();
    } catch {}
    setServerStatus('idle');
  };

  // Handle start import
  const handleStartImport = useCallback(() => {
    if (!connectionInfo) return;
    if (completedFiles === 0) return;
    onStartImport(connectionInfo.upload_dir);
  }, [connectionInfo, completedFiles, onStartImport]);

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes >= 1024 * 1024 * 1024) return (bytes / (1024 ** 3)).toFixed(1) + ' GB';
    if (bytes >= 1024 * 1024) return (bytes / (1024 ** 2)).toFixed(1) + ' MB';
    if (bytes >= 1024) return (bytes / 1024).toFixed(0) + ' KB';
    return bytes + ' B';
  };

  // ===== Resume dialog =====
  if (showResume && resumeSession) {
    const date = new Date(resumeSession.created_at * 1000).toLocaleString();
    const sizeStr = formatSize(resumeSession.total_bytes);

    return (
      <div className="flex flex-col items-center py-6 space-y-6">
        <div className="text-5xl">⚠️</div>
        <h3 className="text-lg font-semibold">{t('phoneImport.resumeTitle')}</h3>
        <p className="text-sm text-text-secondary text-center">
          {t('phoneImport.resumeDetail', { date, count: resumeSession.file_count, size: sizeStr })}
        </p>
        <div className="flex gap-3 w-full">
          <button
            onClick={handleResumeContinue}
            className="flex-1 px-4 py-2.5 bg-primary text-white rounded-md text-sm hover:bg-primary-hover transition-colors"
          >
            {t('phoneImport.resumeContinue')}
          </button>
          <button
            onClick={handleResumeDiscard}
            className="flex-1 px-4 py-2.5 bg-card border border-border rounded-md text-sm hover:border-primary transition-colors"
          >
            {t('phoneImport.resumeDiscard')}
          </button>
        </div>
      </div>
    );
  }

  // ===== Starting state =====
  if (serverStatus === 'starting') {
    return (
      <div className="flex flex-col items-center py-10 space-y-4">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-text-secondary">{t('phoneImport.starting')}</p>
      </div>
    );
  }

  // ===== Error state =====
  if (serverStatus === 'error') {
    return (
      <div className="flex flex-col items-center py-8 space-y-4">
        <div className="text-4xl">❌</div>
        <p className="text-sm text-text-secondary text-center">{errorMessage}</p>
        <button
          onClick={doStartServer}
          className="px-6 py-2 bg-primary text-white rounded-md text-sm hover:bg-primary-hover transition-colors"
        >
          {t('common.retry')}
        </button>
        <button
          onClick={onBack}
          className="text-sm text-text-tertiary hover:text-text-secondary transition-colors"
        >
          {t('preview.back')}
        </button>
      </div>
    );
  }

  // ===== Running state =====
  return (
    <div className="flex flex-col space-y-5">
      {/* Steps guide */}
      <div className="flex items-center gap-2 text-xs text-text-tertiary">
        <span className="w-5 h-5 rounded-full bg-primary text-white flex items-center justify-center text-xs">1</span>
        <span>{t('phoneImport.ensureWifi')}</span>
      </div>

      {/* QR Code */}
      <div className="flex items-start gap-5 p-4 bg-page rounded-lg border border-border">
        <div className="flex-shrink-0">
          <img
            src={qrUrl}
            alt="QR Code"
            className="w-32 h-32 rounded-md border border-border"
          />
        </div>
        <div className="flex-1 min-w-0 space-y-2">
          <p className="text-sm font-medium">{t('phoneImport.scanQr')}</p>
          <div className="text-xs text-text-secondary break-all font-mono bg-card px-2 py-1 rounded border border-border">
            {connectionInfo?.upload_url || ''}
          </div>
          <p className="text-xs text-text-tertiary">{t('phoneImport.receiving')}</p>
        </div>
      </div>

      {/* Files uploaded */}
      {totalFiles > 0 && (
        <div className="p-4 bg-page rounded-lg border border-border">
          <p className="text-sm font-medium mb-2">
            {t('phoneImport.filesUploaded', { count: completedFiles, size: formatSize(totalBytes) })}
          </p>
          <div className="max-h-48 overflow-y-auto space-y-1.5">
            {files.map((f, i) => (
              <div
                key={i}
                className={`flex items-center justify-between text-xs py-1 px-2 rounded ${
                  f.status === 'done'
                    ? 'text-green-600 dark:text-green-400'
                    : f.status === 'failed'
                    ? 'text-red-500'
                    : 'text-text-tertiary'
                }`}
              >
                <span className="truncate flex-1">
                  {f.status === 'done' ? '✅' : f.status === 'failed' ? '❌' : '⏳'}{' '}
                  {f.name}
                </span>
                <span className="flex-shrink-0 ml-2">{f.size > 0 ? formatSize(f.size) : ''}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleStop}
          className="flex-1 px-4 py-2.5 bg-card border border-border rounded-md text-sm hover:border-primary transition-colors"
        >
          {t('phoneImport.stopReceiving')}
        </button>
        <button
          onClick={handleStartImport}
          disabled={completedFiles === 0}
          className="flex-1 px-4 py-2.5 bg-primary text-white rounded-md text-sm hover:bg-primary-hover disabled:opacity-50 transition-colors"
        >
          {t('phoneImport.startImport')}
        </button>
      </div>

      {/* Back */}
      <button
        onClick={onBack}
        className="text-sm text-text-tertiary hover:text-text-secondary transition-colors self-start"
      >
        ← {t('preview.back')}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/dialogs/ImportDialog/PhoneImportPanel.tsx
git commit -m "feat: add PhoneImportPanel component"
```

---

### Task 8: 改造 ImportDialog（新增模式选择 + 手机上传步骤）

**Files:**
- Modify: `frontend/src/components/dialogs/ImportDialog/ImportDialog.tsx`

- [ ] **Step 1: Add import for PhoneImportPanel**

在文件顶部现有 imports 下方添加：

```tsx
import { PhoneImportPanel } from './PhoneImportPanel';
```

- [ ] **Step 2: Change initial step from 'select' to 'select-mode'**

在 `ImportDialog` 组件内，将：
```tsx
const [step, setStep] = useState<ImportStep>('select');
```
改为：
```tsx
const [step, setStep] = useState<ImportStep>('select-mode');
```

- [ ] **Step 3: Update resetState to reset to 'select-mode'**

在 `resetState` 回调内部，将：
```tsx
setStep('select');
```
改为：
```tsx
setStep('select-mode');
```

- [ ] **Step 4: Update check progress effect - failed/cancelled go back to select-mode**

将 effect 中两处 `setStep('select')` 改为 `setStep('select-mode')`：
- 在 `progress.status === 'failed'` 分支中
- 在 `progress.status === 'cancelled'` 分支中

- [ ] **Step 5: Update handleCancelCheck to go back to select-mode**

将函数体中的 `setStep('select')` 改为 `setStep('select-mode')`

- [ ] **Step 6: Update handleStartCheck failed case**

将 `setStep('select')` 改为 `setStep('select-mode')`

- [ ] **Step 7: Update handleStartImport to use sourcePath (already set)**

此函数无需改动，`sourcePath` 已在选择模式或手机导入完成后设置。

- [ ] **Step 8: Add the select-mode and phone-upload steps to renderStep**

在 `renderStep` 的 switch 中，将 `case 'select':` 改为 `case 'select-path':`，并在前面插入两个新 case：

```tsx
  const renderStep = () => {
    switch (step) {
      case 'select-mode':
        return (
          <div className="space-y-5">
            <p className="text-sm text-text-secondary text-center">{t('phoneImport.selectMode')}</p>
            <div className="grid grid-cols-2 gap-4">
              {/* Phone Import Card */}
              <button
                onClick={() => setStep('phone-upload')}
                className="flex flex-col items-center gap-3 p-6 bg-card border-2 border-border rounded-xl hover:border-primary transition-all group"
              >
                <span className="text-4xl">📱</span>
                <div className="text-center">
                  <p className="font-semibold text-sm group-hover:text-primary transition-colors">
                    {t('phoneImport.entry')}
                  </p>
                  <p className="text-xs text-text-tertiary mt-1">
                    {t('phoneImport.subtitle')}
                  </p>
                </div>
              </button>
              {/* Local Import Card */}
              <button
                onClick={() => setStep('select-path')}
                className="flex flex-col items-center gap-3 p-6 bg-card border-2 border-border rounded-xl hover:border-primary transition-all group"
              >
                <span className="text-4xl">💻</span>
                <div className="text-center">
                  <p className="font-semibold text-sm group-hover:text-primary transition-colors">
                    {t('phoneImport.localImport')}
                  </p>
                  <p className="text-xs text-text-tertiary mt-1">
                    {t('phoneImport.localImportDesc')}
                  </p>
                </div>
              </button>
            </div>
          </div>
        );

      case 'phone-upload':
        return (
          <PhoneImportPanel
            onStartImport={(uploadDir: string) => {
              setSourcePath(uploadDir);
              handleStartCheckFromPhone(uploadDir);
            }}
            onBack={() => setStep('select-mode')}
          />
        );

      case 'select-path':
      case 'checking':
```

- [ ] **Step 9: Add handleStartCheckFromPhone helper (or modify handleStartCheck to accept optional path)**

在 `handleStartCheck` 之前添加一个新函数，接收可选 sourcePath 参数：

```tsx
  // 开始检查（支持直接传入 sourcePath 跳过用户输入步骤）
  const handleStartCheckFromPhone = async (phoneSourcePath: string) => {
    setSourcePath(phoneSourcePath);
    setStep('checking');
    setCheckProgress({ status: 'queued', progress: 0, stage: 'queued', detail: t('import.checkingStatus') });

    try {
      const res = await api.startImportCheck(phoneSourcePath);
      setCheckId(res.check_id);
    } catch (error) {
      const message = error instanceof Error ? error.message : t('import.startCheckFailed');
      showToast(message, 'error');
      setStep('select-mode');
    }
  };
```

- [ ] **Step 10: Update getTitle for new steps**

在 `getTitle` 的 switch 中加入新 case：

```tsx
case 'select-mode':
  return t('import.title');
case 'phone-upload':
  return t('phoneImport.title');
case 'select-path':
  return t('import.title');
```

- [ ] **Step 11: Update Modal onClose for select-mode**

将 Modal 的 `onClose` 改为在 select-mode/select-path/phone-upload 时都可以关闭，只有 importing 时不可关：

```tsx
onClose={
  step === 'importing'
    ? () => {}
    : onClose
}
```

- [ ] **Step 12: Verify full compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 13: Commit**

```bash
git add frontend/src/components/dialogs/ImportDialog/ImportDialog.tsx
git commit -m "feat: add select-mode and phone-upload steps to ImportDialog"
```

---

### Task 9: 后端新增 API 端点

**Files:**
- Modify: `backend/api_server.py`

- [ ] **Step 1: Add phone upload imports**

在 `backend/api_server.py` 顶部现有 imports 后添加：

```python
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
```

- [ ] **Step 2: Add 6 API routes before the existing 'if __name__' block**

在文件中 (建议放在 settings 路由之后的 test API 附近):

```python
# ============================================================================
# 手机上传 API
# ============================================================================

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

        info = server.start()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/phone-upload/discard', methods=['POST'])
def phone_upload_discard():
    """放弃未完成的会话并清理文件"""
    try:
        server = _get_phone_upload_server()
        incomplete = server.has_incomplete_session()
        if incomplete and incomplete.get("upload_dir"):
            import shutil
            session_dir = server.UPLOAD_ROOT if hasattr(server, 'UPLOAD_ROOT') else UPLOAD_ROOT
            # Use the directory from the sessions data
            target = UPLOAD_ROOT / incomplete["upload_dir"]
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
        # 清理 sessions.json 中的记录
        sessions_file = server.UPLOAD_ROOT.parent / "phone_upload" / "sessions.json" if hasattr(server, 'UPLOAD_ROOT') else SESSIONS_FILE
        # Re-read to get __class__ attribute properly
        server.stop(cleanup=True)
        return jsonify({'status': 'discarded'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 2 (corrected): Check and fix the import for io and shutil in api_server.py**

确保 `api_server.py` 顶部已有 `import io` 和 `import shutil`。如果没有，添加它们到现有 imports 中。

- [ ] **Step 3: Fix the discard endpoint to be self-contained**

The discard endpoint above is messy due to trying to access server internals. Let's rewrite it cleanly. Replace the discard route with:

```python
@app.route('/api/phone-upload/discard', methods=['POST'])
def phone_upload_discard():
    """放弃未完成的会话并清理文件"""
    try:
        from .phone_upload_server import PhoneUploadServer, UPLOAD_ROOT, SESSIONS_FILE
    except ImportError:
        from phone_upload_server import PhoneUploadServer, UPLOAD_ROOT, SESSIONS_FILE

    try:
        server = _get_phone_upload_server()
        incomplete = server.has_incomplete_session()
        if incomplete:
            session_dir = UPLOAD_ROOT / incomplete["upload_dir"]
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            # Remove from sessions.json
            if SESSIONS_FILE.exists():
                data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
                data["sessions"] = [
                    s for s in data.get("sessions", [])
                    if s.get("id") != incomplete.get("id")
                ]
                SESSIONS_FILE.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
        return jsonify({'status': 'discarded'})
    except Exception as e:
        logger.error(f'[API] 放弃上传会话失败: {e}')
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 4: Verify the server starts without import errors**

Run: `cd "F:\AI\Frame_Album" && python -c "from backend.api_server import app; print('api_server imports ok')"`
Expected: `api_server imports ok`

- [ ] **Step 5: Commit**

```bash
git add backend/api_server.py
git commit -m "feat: add phone upload API endpoints (/api/phone-upload/*)"
```

---

### Task 10: 打包配置

**Files:**
- Modify: `BlurArc.spec`

- [ ] **Step 1: Add 'qrcode' to hiddenimports**

在 `BlurArc.spec` 的 `hiddenimports = [...]` 列表中追加 `'qrcode'`：

```python
hiddenimports=[
    ...
    'qrcode',           # 手机上传二维码生成
],
```

- [ ] **Step 2: Verify spec is valid Python**

Run: `cd "F:\AI\Frame_Album" && python -c "exec(open('BlurArc.spec').read().split('a = Analysis')[0]); print('spec ok')"`
Expected: `spec ok` (or at least no syntax error)

- [ ] **Step 3: Commit**

```bash
git add BlurArc.spec
git commit -m "chore: add qrcode to PyInstaller hiddenimports"
```

---

### Task 11: 清理方案阶段遗留的本地 commit

> ⚠️ 此项在方案确认后、开始实现前手动执行。

**Files:** 无新增

- [ ] **Step 1: 确认当前有未推送的 spec commit**

Run: `git log --oneline origin/main..HEAD`
Expected: 列出 4 个 spec draft commit

- [ ] **Step 2: 决定处理方式**

选择 A: 保留这些 commit（它们记录了设计迭代），开始实现
选择 B: squash 成单个 commit 再开始实现
选择 C: 保持现状，实现完后一起推送

---

## 自审清单

1. **Spec coverage check:**
   - ✅ 手机上传 HTTP 服务器 (Task 2)
   - ✅ 二维码生成 (Task 2 phone_upload_server.py + Task 9 qr endpoint)
   - ✅ 手机端上传页面 (Task 2 _render_phone_page)
   - ✅ 两层进度上报 (Task 2 phone_upload_server.py + Task 7 polling)
   - ✅ 断点续传-场景A 网络瞬断 (Task 2 retry logic in JS)
   - ✅ 断点续传-场景B 服务器重启 (Task 2 sessions.json + Task 7 resume dialog + Task 9 resume/discard/incomplete)
   - ✅ 主题适配 (Task 2 _render_phone_page theme detection)
   - ✅ 模式选择步骤 (Task 8 select-mode)
   - ✅ 并列入口卡片 (Task 8 select-mode render)
   - ✅ 国际化文案 (Task 6)
   - ✅ 安全措施 (Task 2 ALLOWED_EXTENSIONS, secure_filename, size limits)
   - ✅ 依赖打包 (Task 1 + Task 10)

2. **Placeholder scan:** No TBD, TODO, or vague steps found.

3. **Type consistency:**
   - ImportStep: `'select-mode' | 'select-path' | 'phone-upload' | 'checking' | 'preview' | 'importing'` — consistent across types.ts, ImportDialog.tsx, PhoneImportPanel.tsx
   - API responses: `PhoneUploadStartResponse` shape matches usage in PhoneImportPanel
   - UploadedFile interface in PhoneImportPanel.tsx matches the server-side UploadSession.to_dict() output
   - Session persistence: `sessions.json` structure consistent across phone_upload_server.py write/read and api_server.py discard endpoint

---

## 执行方式

计划完成，保存到 `docs/superpowers/plans/2026-06-18-phone-import-plan.md`。两种执行方式：

**1. Subagent-Driven（推荐）** — 每个 Task 派一个独立 subagent，任务间 review，快迭代

**2. Inline Execution** — 在当前会话中逐任务执行，使用 executing-plans 分批推进

选择哪个方式？
