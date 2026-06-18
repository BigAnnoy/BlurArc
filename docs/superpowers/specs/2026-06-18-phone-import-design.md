# 安卓手机无线照片导入 — 设计文档

> 版本: v1.4 | 日期: 2026-06-18 | 状态: 待评审
> v1.4 更新: 临时上传目录从用户主目录改为软件目录（`.config/phone_upload/`），避免 C 盘空间不足
> v1.3 更新: 手机端页面支持主题色切换（跟随桌面端亮色/暗色）
> v1.2 更新: 手机导入与本地导入改为并列入口，新增模式选择步骤
> v1.1 更新: 补充手机端 UI 详细设计、两层进度上报、断点续传策略

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
│  点击「导入」→ 看到两个并列入口：                                  │
│                                                                 │
│  ┌──────────────────────┐  ┌──────────────────────┐             │
│  │       📱             │  │       💻             │             │
│  │   从手机导入          │  │   本地导入            │             │
│  │   扫码无线传输         │  │   从磁盘/U盘选择      │             │
│  └──────────┬───────────┘  └──────────────────────┘             │
│             │                                                    │
│             ▼                                                    │
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
│  点"开始导入"→ 跳转到 Step2Preview 预览界面                      │
│  → 显示去重结果 → 选导入模式(复制/移动) → Step3 执行导入           │
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
 │ (扫码打开) │         │ :9876 (独立端口)   │             │ .config/     │
 └──────────┘          │ QR生成 + 文件接收  │             │ phone_upload/│
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

**Q: 为什么临时目录放在软件目录下而不是用户主目录？**

A: 手机照片可能很大（几百 MB 到几十 GB），用户 C 盘（通常 `C:\Users\xxx` 所在盘）空间可能不足。软件目录（`exe 所在目录或项目根目录`）通常和相册在同盘，空间更有保障。`_get_app_data_dir()` 在打包模式下返回 exe 所在目录，开发模式下返回项目根目录，与现有 `.config/` 的约定一致。

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
    # APP_DATA_DIR 复用 config_manager._get_app_data_dir()
    # 打包模式 = exe 所在目录，开发模式 = 项目根目录
    UPLOAD_ROOT = APP_DATA_DIR / ".config" / "phone_upload"

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
  "upload_dir": "/path/to/BlurArc/.config/phone_upload/20260618_143052/"
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

### 4.6 手机端上传页面（UI 与交互）

服务器直接返回内联 HTML（无前端构建依赖，无外部资源引用）。跟随桌面端主题（暗色/亮色），与 Blur Arc 品牌一致，纯原生 JS 实现。

#### 4.6.1 页面布局

```
┌──────────────────────────────────┐
│          🌐 Blur Arc             │  ← 顶部品牌栏（主题色背景）
│       从手机导入照片              │
├──────────────────────────────────┤
│                                  │
│    ┌──────────────────────┐      │
│    │  📷  选择照片/视频     │      │  ← 大号上传按钮（点击触发文件选择器）
│    │  点击选择或拍照        │      │
│    └──────────────────────┘      │
│                                  │
│    ── 上传进度 ──                 │  ← 分割标题
│                                  │
│    整体: ████████░░ 7/15  68%    │  ← 总进度条 + 文件计数
│          已传 89 MB / 约 131 MB   │
│                                  │
│    当前: IMG_20260618_143052.jpg  │  ← 当前传输文件名
│           ████████████░  92%     │  ← 当前文件进度条
│           ↑ 2.3 MB/s             │  ← 实时速率
│                                  │
│    ── 已完成 (5) ──               │
│                                  │
│    ✅ IMG_001.jpg  3.2 MB        │  ← 已完成列表（绿色勾）
│    ✅ IMG_002.jpg  4.1 MB        │
│    ✅ VID_001.mp4  52 MB         │
│    ✅ IMG_003.jpg  2.8 MB        │
│    ✅ IMG_004.jpg  1.9 MB        │
│                                  │
│    ❌ IMG_005.jpg  上传失败 重试  │  ← 失败项，可点击重试
│                                  │
│    ┌──────────────────────────┐  │
│    │  ⏹ 停止（已上传的保留）    │  │  ← 底部操作按钮
│    └──────────────────────────┘  │
│                                  │
│    💡 上传完成后在电脑端继续操作   │  ← 提示文字
└──────────────────────────────────┘
```

#### 4.6.2 主题适配

手机上传页面作为 Blur Arc 品牌延伸，必须跟随桌面端主题。页面渲染时服务端读取当前主题配置，注入对应 CSS 变量。

**两种主题配色：**

| 元素 | 暗色主题（默认） | 亮色主题 |
|------|-----------------|---------|
| 页面背景 | `#0c1117` | `#f4f7f9` |
| 卡片/区块背景 | `#151d26` | `#ffffff` |
| 品牌栏背景 | `#0c1117`（渐变 primary） | `#ffffff`（渐变 primary-light） |
| 主色调 (primary) | `#22d3ee` | `#0891b2` |
| 主文字 | `#e8f0f5` | `#1a2a3a` |
| 次要文字 | `#8aa0b0` | `#5a6a7a` |
| 进度条底色 | `#1c2836` | `#d8e2e8` |
| 成功绿 | `#4ade80` | `#22c55e` |
| 失败红 | `#f87171` | `#ef4444` |
| 边框 | `#1c2836` | `#d8e2e8` |

**主题注入方式：**

```
服务端渲染 HTML 时:
  config_manager.get_setting('theme', 'system')
    │
    ├── 'dark'   → CSS class "dark"
    ├── 'light'  → CSS class "light"
    └── 'system' → 跟随 `prefers-color-scheme`（CSS media query，无需 JS）

HTML 结构中:
  <html class="dark">  或  <html class="light">
```

CSS 用变量实现，暗色/亮色各一套默认值，无需 JS 切换。`system` 模式直接用 CSS `@media (prefers-color-scheme: dark)` 处理。

**顶部品牌栏细节：**

暗色主题下：
- 背景：`linear-gradient(135deg, #0c1117 0%, #0e3d4a 100%)` — 从 page 色渐变到 primary 深色
- Logo 文字 "Blur Arc"：`#22d3ee`（primary），字重 700，字号 20px
- 副标题 "从手机导入照片"：`#8aa0b0`（text-secondary），字号 13px
- 左侧小圆点装饰：`#22d3ee`（品牌色点缀）

亮色主题下：
- 背景：`linear-gradient(135deg, #f4f7f9 0%, #e0f7fa 100%)` — page 色渐变到 primary-light
- Logo 文字 "Blur Arc"：`#0891b2`（primary），字重 700
- 副标题：`#5a6a7a`（text-secondary）
- 圆点装饰：`#0891b2`

#### 4.6.2 交互流程

| 阶段 | 手机端显示 | 用户操作 |
|------|-----------|---------|
| ① 打开页面 | 品牌栏 + 大号选择按钮 | 点击选择照片/视频，或直接拍照 |
| ② 选择文件 | 系统文件选择器 / 相机 | 单选或多选照片、视频 |
| ③ 上传中 | 总进度条 + 当前文件进度 + 实时速率 | 可随时点「停止」中断 |
| ④ 单文件失败 | 该项标红，显示"重试"链接 | 点击重试单个文件，不影响其他 |
| ⑤ 全部完成 | 所有项绿色 ✅，"全部上传完成" | 切换回电脑端操作 |
| ⑥ 停止 | 已上传项保留，未上传项灰掉 | 需要时可重新打开页面继续 |

#### 4.6.3 进度上报细节

**两层进度：**

```
层级 1 — 总进度:  已完成的文件数 / 选中的总文件数
                  ↓ 进度条百分比按文件数算

层级 2 — 当前文件:  XMLHttpRequest.upload.onprogress 回调
                  已发送字节 / 文件总字节
                  ↓ 实时速率 = Δbytes / Δtime
```

**服务器端 GET /status 返回给电脑端的数据：**

```json
{
  "total_files": 15,
  "completed_files": 7,
  "current_file": "IMG_20260618_143052.jpg",
  "current_progress": 92.3,
  "current_speed_mbps": 2.3,
  "total_bytes_uploaded": 93456789,
  "files": [
    {"name": "IMG_001.jpg", "size": 3200000, "status": "done"},
    {"name": "IMG_005.jpg", "size": 5100000, "status": "failed", "error": "Connection reset"},
    {"name": "IMG_008.jpg", "size": 0, "status": "pending"}
  ]
}
```

状态枚举：`pending` → `uploading` → `done` / `failed`

#### 4.6.4 实现约束

- 单文件 HTML，内联 CSS + JS，无外部资源
- `<input type="file" multiple accept="image/*,video/*">` — 安卓 Chrome 点击后直接拉起系统照片选择器，支持多选
- 文件逐个串行上传（并行会导致手机浏览器内存压力，且进度展示混乱）
- 控制在 ~300 行以内

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

### 5.3 新增模式选择步骤

在现有 ImportDialog 中增加 `step === 'select-mode'`，作为进入导入流程的第一个界面。手机导入和本地导入是**两个并列的一级入口**，用户必须先选择一种模式。

```
┌──────────────────────────────────────────────────────────┐
│                      📥 导入照片                          │
│                                                          │
│  请选择导入方式：                                         │
│                                                          │
│  ┌─────────────────────────┐  ┌─────────────────────────┐│
│  │                         │  │                         ││
│  │        📱               │  │        💻               ││
│  │    从手机导入            │  │    本地导入              ││
│  │                         │  │                         ││
│  │  扫码无线传输            │  │  从本地磁盘/              ││
│  │  无需数据线              │  │  U盘/移动硬盘            ││
│  │                         │  │  选择文件夹              ││
│  │                         │  │                         ││
│  └─────────────────────────┘  └─────────────────────────┘│
│                                                          │
└──────────────────────────────────────────────────────────┘
```

两个卡片等高并排，点击任一卡片进入对应的子流程。

### 5.4 与 ImportDialog 的集成

```
ImportDialog
├── step === 'select-mode'    ← [新增] 两个并列入口卡片
│       │
│       ├── 点击"从手机导入" → step === 'phone-upload'
│       │                      └── PhoneImportPanel
│       │                           上传完成 → setSourcePath(临时目录) → step === 'checking'
│       │
│       └── 点击"本地导入"   → step === 'select-path'
│                              └── Step1Select（现有，不变）
│                                   选择路径 → step === 'checking'
│
├── step === 'checking'       ← 两种模式汇合于此，后续完全一致
├── step === 'preview'
└── step === 'importing'
```

**关键点：** 两种导入模式在 `checking` 步骤汇合。手机导入完成后自动把临时目录路径传给 `sourcePath`，此后走完全相同的预检 → 去重 → 预览 → 导入流程，零差异。

**ImportStep 类型扩展：**

```tsx
type ImportStep = 'select-mode' | 'phone-upload' | 'select-path' | 'checking' | 'preview' | 'importing';
//                  ↑ 新增          ↑ 新增           ↑ 原 'select' 改名
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
POST /api/import/check  { source_path: "/path/to/BlurArc/.config/phone_upload/20260618_143052/" }
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

## 8. 错误处理与断点续传

### 8.1 断点续传策略

手机上传的"断点"分两种场景：

#### 场景 A：网络瞬断（WiFi 波动、手机锁屏等）

**手机端处理：**
- 当前正在上传的文件 → 自动重试 3 次，间隔递增（1s / 3s / 5s）
- 3 次全失败 → 该文件标为 `failed`，**自动跳过，继续传下一个**
- 失败的项在列表中显示 ❌ + "重试"链接，用户可手动点重试
- 已成功的文件不受影响

```
IMG_001 ✅ → IMG_002 ✅ → IMG_003 ❌(超时) → IMG_004 ✅ → IMG_005 ✅
                                     ↓
                           列表中 IMG_003 标红 [重试]
                                     ↓
                           用户点重试 → IMG_003 ✅
```

#### 场景 B：服务器关闭后重新打开（关了弹窗、重启了应用）

这是更强的一类"断点"——上传服务器已停，但已上传的文件还在磁盘上。

**会话持久化机制：**

```
<app_data_dir>/.config/phone_upload/
├── sessions.json                    ← 会话索引
├── 20260618_143052/                 ← 会话 A
│   ├── IMG_001.jpg
│   ├── IMG_002.jpg
│   └── VID_001.mp4
└── 20260618_210315/                 ← 会话 B（后来新建的）
    └── IMG_008.jpg
```

`sessions.json`：
```json
{
  "sessions": [
    {
      "id": "abc123",
      "upload_dir": "20260618_143052",
      "created_at": 1718699452.0,
      "file_count": 3,
      "total_bytes": 60123456,
      "status": "incomplete"
    }
  ]
}
```

**恢复流程：**

```
重新打开「从手机导入」
    │
    ▼
检查 sessions.json 有无 status=="incomplete" 的会话
    │
    ├── 有 → 弹出提示：
    │   ┌──────────────────────────────────────┐
    │   │  ⚠️ 发现上次未完成的导入               │
    │   │                                      │
    │   │  2026-06-18 14:30 — 3 个文件 (57 MB) │
    │   │                                      │
    │   │  [继续上传]  [放弃，重新开始]          │
    │   └──────────────────────────────────────┘
    │       │
    │       ├── 继续上传 → 复用已有 session，启动服务器
    │       │   手机扫码重新打开页面 → 上次文件显示 ✅
    │       │   → 继续选新文件追加
    │       │
    │       └── 放弃 → 删除旧 session 目录，全新开始
    │
    └── 无 → 新建 session，正常流程
```

**说明：** 手机端不会自动记住上次的 URL（浏览器不跨会话保留），需要重新扫码。这可以接受——扫码只是 1 秒的事。

### 8.2 错误处理矩阵

| 场景 | 处理方式 |
|------|---------|
| 端口全部被占用 | 显示明确错误信息，建议关闭占用程序 |
| 防火墙拦截 | 提示用户允许 Blur Arc 通过防火墙（Windows 首次启动会弹系统对话框） |
| 当前文件上传失败（网络瞬断） | 手机端自动重试 3 次，仍失败则跳过，标红 + 手动重试按钮 |
| 手机锁屏或切后台 | 浏览器暂停 JS → 上传中断。解锁后自动重试当前文件 |
| 手机断开 WiFi | 所有进行中的上传失败。已完成的保留。手机页面显示"连接断开"提示 |
| 服务器主动关闭（用户点停止） | 已完成文件保留，sessions.json 标记 incomplete |
| 上传超大文件 | 限制 500MB，超额返回 413，手机端提示 |
| 临时目录磁盘空间不足 | 写入前检查可用空间，不足时停止接收并提示 |
| 手机端上传同样文件两次 | 服务端自动追加序号 `_1`, `_2` 避免覆盖（去重交给后续导入管线） |
| 上传未完成用户点了"开始导入" | 先自动 stop 服务器，再以已上传的文件启动导入 |
| 恢复的会话目录已被手动删除 | 视为"放弃"，直接新建 session |
| 手机端选了一个损坏的 0 字节文件 | 上传完成后校验文件大小，0 字节则拒绝并提示 |

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
- `sessions.json` 读写与 `incomplete` → `completed` 状态转换
- 文件重名自动加序号 `_1`, `_2`

### 集成测试

- 上传 → 停止 → 文件仍在临时目录 → sessions.json 标记 incomplete
- 上传 → 开始导入 → 调用 check → 预览数据正确
- 上传 → 导入完成 → 临时目录被清理 → sessions.json 标记 completed
- 同一文件上传两次 → 去重标记正确
- 模拟会话恢复：incomplete 会话 → 重新打开 → 提示恢复
- 放弃旧会话 → 目录清理

### 手动测试

- 电脑开热点，手机连接 → 扫码上传 → 手机端观察进度条（两层）
- 上传中关闭手机 WiFi → 确认当前文件标红、已完成文件保留
- 上传中手机锁屏 → 解锁后确认自动重试
- 关闭弹窗 → 重新打开 → 确认提示恢复未完成会话
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
