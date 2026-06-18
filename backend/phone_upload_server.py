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
from werkzeug.serving import make_server

from .config_manager import _get_app_data_dir
from .constants import MEDIA_FORMATS

logger = logging.getLogger(__name__)

APP_DATA_DIR = _get_app_data_dir()
UPLOAD_ROOT = APP_DATA_DIR / ".config" / "phone_upload"
SESSIONS_FILE = UPLOAD_ROOT / "sessions.json"
MAX_SINGLE_FILE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_FILES_PER_SESSION = 2000

# 允许的扩展名（复用 constants.py 定义，保持与导入流程一致）
ALLOWED_EXTENSIONS = MEDIA_FORMATS


@dataclass
class UploadedFile:
    """单个已上传文件记录"""
    original_name: str
    saved_path: str
    size: int
    mime_type: str
    uploaded_at: float
    status: str = "done"
    error: str | None = None


class UploadSession:
    """一次上传会话"""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.upload_dir = UPLOAD_ROOT / f"{ts}_{self.session_id[:8]}"
        self.files: list[UploadedFile] = []
        self.done_count: int = 0
        self.total_bytes: int = 0
        self.created_at: float = datetime.now().timestamp()
        self.is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "total_files": len(self.files),
            "completed_files": self.done_count,
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
        self._server = None
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

    def start(self, session: UploadSession | None = None) -> dict:
        """启动服务器。返回 {port, local_ip, upload_url, session_id, upload_dir}
        如果传入 session 参数则复用（用于断点续传），否则创建新会话。"""
        self.port = self._find_free_port()
        if session:
            self._session = session
        else:
            self._session = UploadSession()
        self._session.upload_dir.mkdir(parents=True, exist_ok=True)
        if not session:
            self._write_sessions_json()

        self._server = make_server(self.HOST, self.port, self.app, threaded=False)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
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
        if self._session:
            self._session.is_active = False
            if cleanup:
                self._cleanup_session_dir()
            else:
                self._update_session_status("incomplete")
        if self._server:
            self._server.shutdown()
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
            session.done_count = len(session.files)
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
        if self._session.done_count >= MAX_FILES_PER_SESSION:
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
        self._session.done_count += 1
        self._session.total_bytes += file_size
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
                s["file_count"] = self._session.done_count
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
let allFileNames = [];
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
