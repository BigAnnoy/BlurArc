# Changelog

所有重要变更都记录在本文件中。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [0.5.2] — 2026-06-18

### 新增
- **Flutter 移动端 App**：支持 Android / iOS / 平板，局域网无线浏览相册、推送照片
- **移动接入服务** (`MobileAccessServer`)：独立 Flask 服务（端口 8900-8999），与主 API 隔离
- **mDNS 局域网发现** (`ZeroconfPublisher`)：手机自动发现 PC 端服务，无需手动输入 IP
- **安全配对流程**：6 位配对码 + 设备管理 + Bearer Token 认证
- **移动端 API**（12 个端点）：相册统计、目录树、照片列表、缩略图、原始文件、EXIF、上传
- **PC 端管理界面** (`MobileDeviceManager`)：配对模式开关、QR 二维码、待确认设备列表、撤销设备
- **Token 持久化**：移动端令牌保存到 `.config/mobile_tokens.json`，重启不丢失
- **速率限制**：`/pair` 端点添加 IP 级限流（10 次/分钟），防止暴力破解
- **上传安全控制**：`MAX_CONTENT_LENGTH=500MB` + content-length 预检 + session 文件数限制（2000）

### 变更
- 版本号更新至 v0.5.2
- `backend/api_server.py` 新增 15 个桥接端点（`/api/mobile/*` 和 `/api/mobile/pairing/*`）
- `src/BlurArc.py` 新增 `_start_mobile_service()` 自动启动逻辑
- `frontend/src/services/api.ts` 新增 14 个移动 API 方法
- `frontend/src/contexts/I18nContext.tsx` 新增 22 组中英 i18n 字符串
- `requirements.txt` 新增 `qrcode>=7.4`、`flask-cors>=4.0`、`zeroconf>=0.132.0`

### 修复
- **C1** 缩略图/预览端点类型错误：`Path` 对象改为 `send_file(str(path))`
- **C2** PairingManager 线程安全：添加 `threading.Lock()`，9 个方法全部加锁
- **C3** 上传端点安全控制：添加 `MAX_CONTENT_LENGTH`、`secrets` 生成配对码、过期清理
- **I1** `device_name` 输入验证：空字符串拒绝 + 50 字符限制 + 非法字符过滤
- **I2** 路径校验统一：抽取 `_is_path_safe()` 方法，Windows 大小写不敏感比较
- **I3** `mobile_photos()` 空路径检查：避免 `Path("").resolve()` 返回 CWD
- **I4** `stop_pairing_mode()` 异常处理：捕获 `consume_code()` 可能的异常
- `multicast_dns` API 问题：暂时 stub 处理，使用手动输入 IP 兜底
- Flutter 编译错误：修复 `saveConnection()` 参数个数、`AlbumScreen` 导入、`host`/`port` 公有 getter

### 安全
- 所有文件操作使用 `relative_to()` 路径校验，防止路径穿越
- Token 使用 `secrets.token_urlsafe(32)` 生成，128 位熵
- 配对码使用 `secrets.choice()` 生成，避免 `random` 弱随机数
- 过期 pending 码自动清理（60 秒超时）

### 测试
- 新增 `test/unit/test_mobile_access_server.py`：17 个单元测试
- 新增 `test/unit/test_phone_upload_server.py`：18 个单元测试
- 所有 35 个移动相关测试全部通过 ✅
- Flutter `flutter analyze`：0 issues ✅

---

## [0.5.1] — 2026-06-18

### 新增
- **安卓手机无线导入**：扫码 → 浏览器上传 → 复用现有去重导入管线
- 导入对话框新增模式选择步骤，手机导入和本地导入并列入口
- 手机端上传页面支持主题色（暗色/亮色）跟随桌面端

### 变更
- 版本号更新至 v0.5.1

### 依赖
- 新增 `qrcode>=7.4`（二维码生成）

---

## [0.5.0] — 2026-06-16

### 变更
- **项目重命名**：从 FrameAlbum 更名为 Blur Arc，统一品牌标识
- **版本号标准化**：所有配置文件、文档、安装包统一为 v0.5.0
- **文档重构**：README.md 重写，更简洁专业

### 修复
- 修复前端构建后仍显示旧名称的问题
- 修复多处版本号不一致问题

---

## [0.4.0] — 2026-06-16

### 新增
- **FFmpeg 8.1.1 集成**：视频缩略图生成、元数据提取功能完整可用
- **MD5 缓存复用**：一次导入中每个文件只计算一次 MD5，结果缓存复用
- **并行源文件去重**：使用 ThreadPoolExecutor 并行计算 MD5
- **两阶段预筛优化**：按文件大小分组，只对大小相同的文件组计算 MD5
- **快速文件指纹**：新增 `get_file_fingerprint()` 函数，用于快速预筛
- **前端架构升级**：React 19 + TypeScript + Vite + Tailwind CSS

### 性能提升
| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| 1000 文件无重复 | 全算 MD5 | 0 个算 MD5 |
| 源文件去重 | 串行计算 | 并行计算 |
| 同文件 MD5 | 最多 3 次 | 只 1 次 |

### 变更
- 前端从原生 JS 重构为 React + TypeScript
- `_load_target_records()` 返回值改为 `Tuple[Dict, Dict]`，增加文件大小索引
- `_import_file()` 增加 `md5_cache` 参数支持缓存复用
- `utils.py` 新增 `get_file_fingerprint()` 函数

### 文档
- 新增 `项目分析报告.md`
- 新增 `docs/API_REFERENCE.md`
- 新增 `docs/DATABASE_SCHEMA.md`
- 新增 `docs/DEVELOPMENT_GUIDE.md`
- 更新 `README.md` 版本信息和功能说明

---

## [0.3.0] — 2026-03-25

### 新增
- **导入模式弹窗**：点击「开始导入」时弹出选择框，支持「复制」（保留源文件）和「移动」（导入后删源文件）两种模式，取代原来的常驻切换按钮
- **导入暂停/继续**：多线程导入过程中可随时暂停/继续，进度不丢失
- **全局多选交互**：长按或点击勾选框进入多选模式，支持相册主页和导入预检三个 Tab 的批量操作
- **批量删除**：相册主页和导入对话框均支持多选后一键删除，附带确认对话框防误操作
- **时间线 Tab 删除功能**：导入预检的时间线 Tab 新增删除所选文件按钮
- **相册主页常驻删除按钮**：工具栏新增轮廓风格删除按钮，点击快速进入多选模式
- **视频原生播放**：HTTP Range 支持任意 Seek，自动显示时长/分辨率/编码信息
- **HEIC 等特殊格式预览**：HEIC / TIFF / BMP / ICO 自动转 JPEG 缩略图
- **右键菜单**：照片卡片右键弹出「预览 / 打开文件 / 删除」上下文菜单
- **预览翻页**：预览模态框支持 ← → 键翻页，显示「3/12」索引徽标
- **Toast 通知系统**：操作反馈改为右下角滑入动画 Toast，不打断操作流
- **删除确认对话框**：批量删除前弹出确认，避免误操作
- **帮助页面**：模态框形式，含快捷键说明和关于信息
- **统计信息扩展**：新增视频文件数量和时间跨度统计

### 修复
- `import_manager.py` 多线程重复复制竞态：用 `file_lock` 保证「MD5查重→路径解析→复制→记录」原子性
- `api_server.py` 目标重复检测改为两阶段：(size, exif_time) 预筛 + MD5 精确比对，大幅减少 I/O
- `video_processor.py` duration 取值：mkv/ts 等格式优先从 format.duration 回落取时长
- `thumbnail_manager.py` 调色板透明图：`'P'` 模式图片先 `convert('RGBA')` 再取 alpha mask
- `album-browser.js` `photo.thumbnail` → `photo.thumbnail_url`
- `video_processor.py` FFmpeg 参数：`-format/-quality` → `-f image2 -q:v 2`

### 变更
- 文件命名规则改为 `YYYYMMDD_HHmmss_001.ext`（纯日期时间序号，废弃旧版中文前缀）
- 重复文件加 `_dup` 后缀保留，供用户手动审查
- `get_config_manager()` 改为复用模块单例，避免重复初始化

---

## [0.2.0] — 2026-03-24

### 新增
- PyWebView + Flask 全新架构，替换旧版 Tkinter UI
- 现代化 Web 前端（单页应用，响应式布局）
- 相册目录树浏览
- 导入预检：时间线 Tab / 目标重复 Tab / 源重复 Tab
- 缩略图缓存机制
- 配置文件 `.config/config.json` + SQLite 双层存储

---

## [0.1.0] — 2026-03-23

### 新增
- 初始版本：单文件 Python 脚本
- EXIF 日期读取，按 `YYYY/YYYY-MM` 归档
- MD5 去重
- 支持 JPG / PNG / HEIC / MP4 / MOV 等常见格式
