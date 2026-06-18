# 安卓手机无线照片导入 — 设计文档

> 版本: v1.0 | 日期: 2026-06-18 | 状态: 待评审

---

## 1. 概述

### 1.1 动机

当前 Blur Arc 导入流程要求用户先通过文件浏览器选择源路径，适用于本地磁盘和 U 盘，但不适合安卓手机场景——手机照片在 DCIM 目录下，通过 MTP 访问路径不稳定。用户希望扫码即传、传完即用。

### 1.2 目标

在不改变现有导入去重流程的前提下，新增一个**无线 HTTP 上传**通道：电脑端启动临时局域网服务器 → 生成二维码 → 手机扫码打开上传页 → 选照片上传 → 落入临时目录 → **自动复用现有导入流程**完成去重和归档。

### 1.3 非目标

- 不支持 iOS 设备（iOS 浏览器文件选择器限制较多，后续评估）
- 不做增量同步 / 自动备份（这不是云同步工具）
- 不引入外部云服务中转（纯局域网点对点）

---

## 2. 用户流程

```
┌─────────────────────────────────────────────────────────────────┐
│  电脑端 Blur Arc                                                │
│                                                                 │
│  点击「导入」→ 看到"从手机导入"入口 → 点击 →                     │
│  ┌─────────────────────────────────────────┐                    │
│  │  📱 从手机导入                           │                    │
│  │                                         │                    │
│  │  ① 确保手机和电脑在同一 WiFi 网络          │                    │
│  │                                         │                    │
│  │  ② 手机扫码或浏览器输入地址                │                    │
│  │     ┌──────────────┐    http://192.168.1.5:9876              │
│  │     │  ██████████  │                    │                    │
│  │     │  ██ QR ████  │                    │                    │
│  │     │  ██████████  │                    │                    │
│  │     └──────────────┘                    │                    │
│  │                                         │                    │
│  │  ③ 在手机上选择照片上传                   │                    │
│  │                                         │                    │
│  │  [已上传: 12 张, 共 156 MB]              │                    │
│  │  [停止接收]  [开始导入]                   │                    │
│  └─────────────────────────────────────────┘                    │
│                                                                 │
│  点"开始导入"→ 跳转到现有 Step2Preview 预览界面                  │
│  → 显示去重结果 → 选导入模式 → Step3 执行导入                     │
└─────────────────────────────────────────────────────────────────┘
```

### 关键交互细节

| 步骤 | 用户操作 | 系统响应 |
|------|---------|---------|
| 进入 | 点击"从手机导入" | 后端启动上传服务器，前端显示二维码和状态 |
| 上传中 | 手机端选文件上传 | 实时显示已上传数量、总大小、当前传输文件名 |
| 停止接收 | 点击"停止接收" | 关闭上传服务器，保留已上传文件 |
| 开始导入 | 点击"开始导入" | 以临时目录为源路径调用 `/api/import/check`，进入现有预览流程 |
| 取消 | 关闭弹窗 | 停止服务器，清理临时文件 |

---

## 3. 架构设计

### 3.1 整体数据流

```
 ┌──────────┐  WiFi    ┌──────────────────┐  HTTP POST   ┌──────────────┐
 │ 手机浏览器 │ ◄─────► │ Flask upload svr  │ ──────────► │  临时目录     │
 │ (扫码打开) │         │ :9876 (独立端口)   │             │ ~/.blurarc/   │
 └──────────┘          │ QR生成 + 文件接收  │             │ phone_upload/ │
                       └────────┬─────────┘             └──────┬───────┘
                                │                              │
                                │ 用户点"开始导入"               │
                                ▼                              │
                       ┌──────────────────┐                    │
                       │ 现有 ImportDialog │ ◄──────────────────┘
                       │ Step1Select       │   源路径 = 临时目录
                       │ 自动填入源路径      │
                       └────────┬─────────┘
                                │ /api/import/check
                                ▼
                       ┌──────────────────┐
                       │ 现有去重流程       │
                       │ 两阶段预筛 + MD5   │
                       │ 预览 → 确认 → 导入 │
                       └──────────────────┘
```

### 3.2 关键决策

**Q: 为什么用独立端口而不是复用 Flask 主服务器？**

A: 文件上传是长连接 + 大 body 操作，复用主服务器会阻塞缩略图、API 等正常请求。独立端口隔离上传流量，不影响主应用使用。上传完即关闭。

**Q: 为什么不在手机上装 App？**

A: 零安装门槛是这个功能的核心价值。浏览器原生的 `<input type="file" multiple accept="image/*,video/*">` 足够好，且无需维护移动端代码。

---

## 4. 后端设计

### 4.1 新增模块: `backend/phone_upload_server.py`

```
backend/
├── phone_upload_server.py    ← 新增：独立上传服务器
├── api_server.py
├── import_manager.py
└── ...
```

**职责:**
- 在随机可用端口启动 Flask 实例（独立于主 API 服务器）
- 提供手机端上传 HTML 页面
- 接收 multipart 文件上传
- 推送上传进度给电脑端（SSE 或轮询）
- 管理上传会话生命周期

**核心类设计:**

```python
class PhoneUploadServer:
    """手机上传服务器，独立端口运行"""

    HOST = "0.0.0.0"        # 监听所有网卡，允许手机访问
    PORT_RANGE = (9800, 9900)  # 自动选择可用端口
    UPLOAD_ROOT = Path.home() / ".blurarc" / "phone_upload"

    def __init__(self):
        self.app = Flask(__name__)
        self.port: int | None = None
        self.thread: threading.Thread | None = None
        self.session: UploadSession | None = None
        self._register_routes()

    def start(self) -> dict:
        """启动服务器，返回 {port, local_ip, qr_data_url}"""
        ...

    def stop(self):
        """停止服务器，清理会话"""
        ...

    def _register_routes(self):
        """注册路由"""
        @self.app.route('/')
        def upload_page():
            """返回手机端上传页面 HTML"""
            ...

        @self.app.route('/upload', methods=['POST'])
        def receive_file():
            """接收单个文件上传，保存到临时目录"""
            ...

        @self.app.route('/status')
        def upload_status():
            """返回当前上传进度（SSE 或 JSON）"""
            ...
```

### 4.2 上传会话模型

```python
@dataclass
class UploadedFile:
    """单个已上传文件的记录"""
    original_name: str
    saved_path: str      # 临时目录中的实际路径
    size: int            # 字节
    mime_type: str
    uploaded_at: float   # timestamp

class UploadSession:
    """一次上传会话"""
    session_id: str          # UUID
    upload_dir: Path         # 本次上传的临时子目录
    files: list[UploadedFile]
    total_bytes: int
    created_at: float
    is_active: bool
```

每次"从手机导入"打开时创建一个新 session，子目录名用时间戳避免冲突（如 `phone_upload/20260618_143052/`）。

### 4.3 新增 API 端点（主 Flask 服务器）

在主 `api_server.py` 中新增两个轻量端点，用于前端控制和查询：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/phone-upload/start` | 启动上传服务器，返回连接信息 |
| POST | `/api/phone-upload/stop` | 停止上传服务器 |
| GET | `/api/phone-upload/status` | 获取当前上传进度 |
| GET | `/api/phone-upload/qr` | 获取二维码图片（PNG，前端用 `<img>` 直接显示） |

**`POST /api/phone-upload/start` 响应:**
```json
{
  "port": 9876,
  "local_ip": "192.168.1.5",
  "upload_url": "http://192.168.1.5:9876",
  "session_id": "abc123",
  "upload_dir": "/home/user/.blurarc/phone_upload/20260618_143052/"
}
```

### 4.4 二维码生成

使用 `qrcode` 库（纯 Python，pip 安装约 50KB）在上传服务器启动时实时生成。直接将 QR PNG 字节流返回给前端，不落盘。

```python
import qrcode
import io

def generate_qr_png(url: str) -> bytes:
    img = qrcode.make(url, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()
```

`requirements.txt` 新增依赖: `qrcode>=7.4`

### 4.5 安全措施

| 措施 | 说明 |
|------|------|
| 仅局域网 | 绑定 `0.0.0.0` 但告知用户"确保同一 WiFi"。不做 IP 白名单（家庭局域网足够安全） |
| 文件名校验 | 接收时过滤 `../` 等路径穿越字符，用 `werkzeug.utils.secure_filename` 处理 |
| 大小限制 | 单文件最大 500MB，单次会话最多 2000 个文件 |
| 会话隔离 | 每次打开"从手机导入"新建子目录，关闭即清理 |
| 临时服务器 | 仅在用户主动开启时运行，关闭弹窗即停止 |
| 格式白名单 | 仅接受 `MEDIA_FORMATS` 中定义的图片和视频格式 |

### 4.6 手机端上传页面

服务器直接返回内联 HTML（无前端构建依赖，无外部资源引用）。样式使用极简暗色主题，与 Blur Arc 品牌一致。

核心功能:
- 多文件选择 `<input multiple accept="image/*,video/*">`
- 上传进度条 (XMLHttpRequest + `upload.onprogress`)
- 已上传文件列表（缩略图预览 + 文件名 + 大小）
- "全部上传完成"提示

不引入任何 JS 框架，纯原生实现，控制在单文件 200 行以内。

---

## 5. 前端设计

### 5.1 新增组件

```
frontend/src/components/dialogs/ImportDialog/
├── PhoneImportPanel.tsx    ← 新增：手机导入面板
├── Step1Select.tsx         ← 现有：添加"从手机导入"入口按钮
└── ...
```

### 5.2 PhoneImportPanel 组件

```tsx
interface PhoneImportPanelProps {
  onStartImport: (sourcePath: string) => void;  // 回调到 ImportDialog
  onClose: () => void;
}
```

**状态管理:**
```
states:
  - serverStatus: 'idle' | 'starting' | 'running' | 'error'
  - connectionInfo: { port, local_ip, upload_url } | null
  - uploadedFiles: UploadedFile[]
  - totalSize: number
  - errorMessage: string | null
```

**渲染三个子状态:**

1. **启动中** — spinner + "正在启动上传服务..."
2. **运行中** — 二维码 + 连接地址 + 实时文件列表 + [停止接收] [开始导入] 按钮
3. **错误** — 错误信息 + 重试按钮（常见：防火墙拦截、端口被占）

**轮询:** 每 1 秒 GET `/api/phone-upload/status`，更新文件列表。

### 5.3 Step1Select 改动

在现有路径输入框上方增加一个入口：

```
┌──────────────────────────────────────┐
│  📱 从手机导入（扫码无线传输）    →   │  ← 新增卡片式入口
├──────────────────────────────────────┤
│  或手动选择源路径：                   │
│  [________________] [📁]             │  ← 现有 UI
│  [开始检查]                           │
└──────────────────────────────────────┘
```

点击"从手机导入"→ Step1Select 切换为 PhoneImportPanel。用户完成上传后点"开始导入"→ 自动填入 sourcePath → 切换到 `checking` 步骤，后续流程完全不变。

### 5.4 与 ImportDialog 的集成

```
ImportDialog
├── step === 'select'
│   ├── [新增] PhoneImportEntry → 点击展开 PhoneImportPanel
│   └── Step1Select (现有，始终可见)
├── step === 'checking'     ← PhoneImportPanel 回调 setSourcePath + setStep
├── step === 'preview'      ← 去重结果预览，不变
└── step === 'importing'    ← 导入执行，不变
```

---

## 6. 国际化

新增文案：

| Key | 中文 | English |
|-----|------|---------|
| `phoneImport.title` | 从手机导入 | Import from Phone |
| `phoneImport.ensureWifi` | 确保手机和电脑在同一 WiFi 网络 | Make sure phone and PC are on the same WiFi |
| `phoneImport.scanQr` | 手机扫码或浏览器访问以下地址 | Scan QR code or visit the address below |
| `phoneImport.starting` | 正在启动上传服务... | Starting upload service... |
| `phoneImport.receiving` | 等待手机上传... | Waiting for uploads... |
| `phoneImport.filesUploaded` | 已上传 {count} 个文件，共 {size} | {count} files uploaded, {size} total |
| `phoneImport.stopReceiving` | 停止接收 | Stop Receiving |
| `phoneImport.startImport` | 开始导入 | Start Import |
| `phoneImport.noFiles` | 请先上传至少一个文件 | Please upload at least one file first |
| `phoneImport.serverError` | 上传服务启动失败，请检查防火墙设置 | Failed to start upload service, check firewall |
| `phoneImport.entry` | 从手机导入 | Import from Phone |

---

## 7. 去重流程（复用现有）

手机上传的去重**零新增代码**，完全复用现有两阶段管线：

```
手机上传完成 → 临时目录作为 sourcePath
    │
    ▼
POST /api/import/check  { source_path: "/home/.../phone_upload/20260618_143052/" }
    │
    ▼ (现有逻辑)
扫描临时目录 → 按文件大小分组 → 对大小相同组计算 MD5
    │
    ▼ (现有逻辑)
与相册已有文件比对 → 标记重复 → 返回 CheckResult
    │
    ▼
Step2Preview 显示：时间线 / 目标重复 / 源重复
    │
    ▼
用户确认 → 开始导入 → 复制/移动到相册 → 清理临时目录
```

**关键点:** 手机拍的照片 EXIF 里有拍摄时间，现有 `YYYY/YYYY-MM/` 归档逻辑对手机照片同样有效。如果同一张照片多次上传，MD5 相同 → 标记为目标重复 → 自动跳过。

---

## 8. 错误处理

| 场景 | 处理方式 |
|------|---------|
| 端口全部被占用 | 显示明确错误信息，建议关闭占用程序 |
| 防火墙拦截 | 提示用户允许 Blur Arc 通过防火墙（Windows 首次启动会弹系统对话框） |
| 手机断开 WiFi 中断上传 | 已上传文件保留，用户可重连后继续或直接开始导入已接收的文件 |
| 上传超大文件 | 限制 500MB，超额返回 413，前端提示 |
| 临时目录磁盘空间不足 | 写入前检查可用空间，不足时停止接收并提示 |
| 手机端上传同样文件两次 | 在临时目录层面不做去重（去重交给后续导入管线）。服务端自动追加序号 `_1`, `_2` 避免覆盖 |
| 上传未完成用户点了"开始导入" | 先自动调用 stop，再以已上传的文件启动导入 |

---

## 9. 依赖与打包

### 新增依赖

| 包 | 版本 | 用途 | 大小 |
|----|------|------|------|
| `qrcode` | >=7.4 | 生成二维码 | ~50KB |
| `pillow` | 已有 | qrcode 依赖（已安装） | - |

### PyInstaller 打包

`qrcode` 是纯 Python 包，无需额外二进制，`BlurArc.spec` 的 `hiddenimports` 新增 `'qrcode'` 即可。

---

## 10. 测试要点

### 单元测试

- `PhoneUploadServer` 启动/停止生命周期
- 文件接收路径安全过滤
- 会话隔离（两次打开不共享文件）
- 端口自动选择逻辑

### 集成测试

- 上传 → 停止 → 文件仍在临时目录
- 上传 → 开始导入 → 调用 check → 预览数据正确
- 上传 → 导入完成 → 临时目录被清理
- 同一文件上传两次 → 去重标记正确

### 手动测试

- 电脑开热点，手机连接 → 扫码上传（真实 WiFi 环境）
- 路由器局域网场景
- Windows 防火墙弹窗确认后功能正常

---

## 11. 实现阶段

| 阶段 | 内容 | 预估 |
|------|------|------|
| **Phase 1** | `phone_upload_server.py` + 手机端 HTML 页面 + 二维码生成 | 核心 |
| **Phase 2** | 主 API 新增端点 + PhoneImportPanel 前端组件 | 集成 |
| **Phase 3** | Step1Select 入口改动 + ImportDialog 状态机扩展 | 串联 |
| **Phase 4** | 错误处理完善 + 测试 + 打包验证 | 收尾 |

---

## 12. 风险与备选

| 风险 | 影响 | 缓解 |
|------|------|------|
| HTTPS 限制：手机浏览器可能不允许 HTTP 访问文件 API | 部分 Android 浏览器限制 `accept` 属性 | 已在 Chrome Android 验证通过；提供"用 Chrome 打开"提示 |
| 部分用户不会连 WiFi | 找不到设备 IP | 入口页面展示本机所有 IP 地址，引导用户 |
| 大量文件上传浏览器可能 OOM | 手机内存不足 | 提示单次不要超过 500 张；分批上传 |
