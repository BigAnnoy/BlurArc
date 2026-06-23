# Blur Arc — Code Map

> 一图速查：模块定位、入口点、关键调用链、改某功能时去哪改。

最后更新：2026-06-22

---

## 📁 顶层结构

```
f:\AI\Frame_Album\
├── src/BlurArc.py              ← 主入口（Flask + PyWebView 启动）
├── backend/                    ← Python 后端（Flask 路由 + 业务）
├── frontend/                   ← PC 端 Web UI（React + TS + Vite）
├── blurarc_app/                ← Flutter 移动 App
├── scripts/                    ← 启动 / 构建 / 测试脚本
├── docs/                       ← 文档、设计稿、devlog、原型
└── test/                       ← Python 后端测试
```

| 目录 | 作用 | 改这个找这里 |
|------|------|-------------|
| `src/BlurArc.py` | 启动入口：路径适配 + Flask + PyWebView 窗口 | 加全局钩子、改启动参数 |
| `backend/` | 后端核心（API、DB、导入、缩略图、视频） | 加接口、改导入逻辑 |
| `frontend/` | PC 端 Web 界面 | 改 PC 端 UI |
| `blurarc_app/` | 移动 App（Dart） | 改移动端 UI / 交互 |
| `docs/devlogs/` | 每日开发日志 | 看历史变更 |
| `docs/prototypes/` | UI 原型（HTML） | 改 UI 前先对齐原型 |
| `docs/superpowers/specs/` | 方案/设计文档 | 改架构前先看设计 |
| `scripts/dev-start.bat` | 开发启动菜单 | 加启动选项、热更新 |

---

## 🐍 后端 (Python + Flask)

### 启动入口链
```
src/BlurArc.py
  └─ main()  [line 304]
     ├─ start_flask_server()     [line 248]  ← 启动 Flask
     │  └─ backend/api_server.py::app.run()
     └─ _start_mobile_service()   [line 285]  ← 移动接入 + mDNS
        └─ backend/mobile_access_server.py::MobileAccessServer.start()
           └─ backend/zeroconf_publisher.py::ZeroconfPublisher.start()
```

### `backend/` 模块地图

| 文件 | 关键类/函数 | 职责 | 改这个 → |
|------|------------|------|---------|
| `api_server.py` | Flask `app` (单例) | **PC 端 API 总入口** | 改任何 PC 端接口 |
| `api_server.py` | `get_album_path()` [L114] | 取当前相册目录（移动端鉴权也用） | 改相册根目录解析 |
| `api_server.py` | `/api/import/*` [L1931-2187] | 导入预检 / 启动 / 进度 / 暂停 | 改导入流程 |
| `api_server.py` | `/api/files/delete` [L2187] | 删除文件 | 改删除逻辑 |
| `api_server.py` | `/api/album/*` [L278-794] | 相册树、照片列表、缩略图、EXIF | 改 PC 浏览页 |
| `api_server.py` | `/api/settings/*` [L863-1206] | 设置：相册路径、FFmpeg、语言、主题 | 改设置项 |
| `api_server.py` | `/api/mobile/*` (L1386-1525, L2582-2659) | 移动端：配对、令牌、设备管理 | 改配对流程 |
| `api_server.py` | `/api/phone-upload/*` [L1234-1315] | PC 端用手机拍照上传 | 改 PC 端拉手机照片 |
| `import_manager.py` | `ImportManager` [L170] | 导入业务：扫描、MD5 去重、复制 | 改去重 / 导入策略 |
| `import_manager.py` | `ImportManager._import_file()` [L535] | 单文件导入（含 MD5 比对） | 改单文件处理 |
| `import_manager.py` | `ImportManager._do_import()` [L251] | 整个导入任务主循环 | 改导入主流程 |
| `import_manager.py` | `ImportManager._compute_md5()` [L696] | MD5 计算（带缓存） | 改 MD5 逻辑 |
| `import_manager.py` | `ImportProgress` [L63] | 进度上报数据结构 | 改进度字段 |
| `database.py` | `Photo` / `Tag` / `Album` 等 [L36-121] | SQLAlchemy ORM 模型 | 改表结构（破坏性！） |
| `thumbnail_manager.py` | `ThumbnailManager` | 缩略图生成/缓存（用户目录跨相册共享） | 改缩略图策略 |
| `video_processor.py` | `VideoProcessor` | FFmpeg 集成：元数据、缩略图 | 改视频处理 |
| `mobile_access_server.py` | `MobileAccessServer` [L325] | **移动接入独立 Flask 应用** | 改移动端 API |
| `mobile_access_server.py` | `PairingManager` [L65] | 移动端配对：码生成、待确认队列 | 改配对状态机 |
| `mobile_access_server.py` | `TokenManager` [L191] | 移动端令牌生成 / 验证 / 撤销 | 改 Token 逻辑 |
| `mobile_access_server.py` | `/api/mobile/file` [L813] | **原图下载**（移动端大图查看用） | 改原图服务 |
| `mobile_access_server.py` | `/api/mobile/thumbnail` [L778] | 缩略图（带 token 鉴权） | 改移动端缩略图 |
| `mobile_access_server.py` | `/api/mobile/upload` [L915] | 移动端上传到 PC | 改手机推送流程 |
| `zeroconf_publisher.py` | `ZeroconfPublisher` | **mDNS 广播**（手机自动发现 PC） | 改 mDNS |
| `config_manager.py` | `ConfigManager` | 用户配置（`~/.photo_organizer_config.json`） | 加配置项 |
| `utils.py` | `get_local_ip()`、`compute_md5()` | 工具函数 | 加通用工具 |
| `constants.py` | 路径、端口、默认值常量 | 改默认端口/路径 |
| `phone_upload_server.py` | （手机推流的旧实现，部分保留） | 兼容旧版 |

### 后端关键路径常量

| 用途 | 位置 |
|------|------|
| 相册根目录 | `backend/api_server.py::get_album_path()` |
| 数据库文件 | `<root>/.config/photo_manager.db`（开发） / `<exe>/.config/`（打包） |
| 缩略图缓存 | `~/.photomanager/thumbnails/` |
| 用户配置 | `~/.photo_organizer_config.json` |
| FFmpeg | `backend/ffmpeg_binaries/ffmpeg.exe` |
| 媒体文件组织 | `<album>/YYYY/YYYY-MM/<filename>` |

---

## ⚛️ 前端 (React + TypeScript + Vite)

### `frontend/src/` 模块地图

| 路径 | 关键文件 | 职责 | 改这个 → |
|------|---------|------|---------|
| `App.tsx` | `AppContent` [L36] | 根状态机（相册/年/照片/选择/分页） | 改顶层状态、加全局事件 |
| `main.tsx` | — | React 入口 | 改 Provider 顺序 |
| `services/api.ts` | `api` [L38] | **所有后端调用**（单文件聚合） | 改 / 加 API 调用 |
| `types/index.ts` | — | TS 类型（Photo、DirNode、YearNode 等） | 改数据结构 |
| `utils/format.ts` | `formatSize` 等 | 格式化工具 | 改显示格式 |
| `hooks/useTheme.ts` | — | 暗/亮主题切换 | 改主题 |
| `contexts/I18nContext.tsx` | `useI18n()` | 国际化（zh/en） | 加语言、改文案 |
| `components/layout/Header.tsx` | — | 顶部栏（菜单/设置/导入） | 改顶部 |
| `components/layout/Sidebar.tsx` | — | 侧边栏（年/月导航） | 改侧边栏 |
| `components/layout/MainContent.tsx` | — | 主内容区（标题栏+网格+选择工具栏） | 改选择删除功能 |
| `components/photos/PhotoCard.tsx` | — | 单张照片卡片（含选中态） | 改卡片样式 |
| `components/photos/PhotoGrid.tsx` | — | 照片网格 | 改网格布局 |
| `components/dialogs/ImportDialog/` | `ImportDialog.tsx` | 导入向导（含 3 个 Step） | 改导入流程 |
| `components/dialogs/ImportDialog/Step1Select.tsx` | — | 选源/目标 | 改选源/选目标 |
| `components/dialogs/ImportDialog/Step2Preview.tsx` | — | 预检结果（重复分类） | 改预检展示 |
| `components/dialogs/ImportDialog/Step3Importing.tsx` | — | 导入进度 | 改进度条 |
| `components/dialogs/ImportDialog/PhoneImportPanel.tsx` | — | 从手机拉照片（PC 端拉手机） | 改手机拉流 |
| `components/dialogs/SettingsDialog.tsx` | — | 设置弹窗 | 改设置 UI |
| `components/dialogs/PhotoPreview.tsx` | — | 大图预览 | 改预览 UI |
| `components/dialogs/MobileDeviceManager.tsx` | — | 移动设备管理（PC 端看手机列表） | 改设备管理 |
| `components/dialogs/DeleteConfirmDialog.tsx` | — | 删除确认 | 改删除提示 |
| `components/common/Logo.tsx` | — | Logo SVG | 改 logo |
| `components/common/Modal.tsx` | — | 通用弹窗 | 改弹窗样式 |
| `components/common/Toast.tsx` | — | 全局 Toast | 改提示样式 |
| `components/WelcomeScreen.tsx` | — | 首次启动欢迎页 | 改首启 |

### 前端数据流

```
App.tsx (state)
  ├─ Header       → 触发 openImportDialog / openSettings
  ├─ Sidebar      → 改 selectedPath / selectedTitle
  └─ MainContent  → 显示 photos
       ├─ PhotoGrid   → 渲 PhotoCard × N
       └─ PhotoCard   → 触发 onPhotoClick → PhotoPreview

导入流程:
  ImportDialog
    Step1: 选源/目标 → api.importCheck(...)
    Step2: 展示预检结果（源重复 / 目标重复 / 时间线）
    Step3: api.importStart(...)
           轮询 api.importProgress(id)
```

### 前端 `api.ts` 常用方法速查

| 方法 | 后端端点 | 用途 |
|------|---------|------|
| `api.health()` | `/api/health` | 健康检查 |
| `api.getStats()` | `/api/album/stats` | 相册统计 |
| `api.getTree()` | `/api/album/tree` | 目录树（已分组成 YearNode） |
| `api.getPhotos(path, page)` | `/api/album/photos` | 某路径下的照片 |
| `api.getThumbnailUrl(path)` | — | 缩略图 URL |
| `api.getFileUrl(path)` | — | 原图 URL |
| `api.importCheck(...)` | `/api/import/check` | 启动预检 |
| `api.importStart(...)` | `/api/import/start` | 启动导入 |
| `api.importProgress(id)` | `/api/import/progress/<id>` | 轮询进度 |
| `api.importCancel/Pause/Resume` | 同前缀 | 导入控制 |
| `api.deleteFiles(paths)` | `/api/files/delete` | 删除 |
| `api.getMobileStatus()` | `/api/mobile/status` | 移动接入开关 |
| `api.startPairing()` / `api.confirmPairing(code)` | `/api/mobile/pairing/*` | 配对 |

---

## 📱 Flutter App (移动端)

### `blurarc_app/lib/` 模块地图

| 路径 | 关键 | 职责 | 改这个 → |
|------|------|------|---------|
| `main.dart` | `BlurArcApp` | 入口 + Provider 初始化 | 改启动屏/全局 Provider |
| `screens/connect_screen.dart` | `ConnectScreen` | 设备发现 + 发起配对 | 改连接页 |
| `screens/pairing_code_screen.dart` | `PairingCodeScreen` | 输入 PC 端显示的配对码 | 改配对码输入 |
| `screens/home_page.dart` | `HomePage` | 主壳（侧边栏 + 底部 Tab） | 改主框架 |
| `screens/album_screen.dart` | `AlbumScreen` + `_SectionBlock` | 按月份分组的照片墙 | 改相册网格 |
| `screens/album_screen.dart` | 双指缩放逻辑 | `onScaleStart/Update/End` | 改列数规则 |
| `screens/folder_screen.dart` | `FolderScreen` | 文件夹浏览 | 改文件夹页 |
| `screens/month_photo_screen.dart` | `MonthPhotoScreen` | 单月照片平铺 | 改月度视图 |
| `screens/photo_grid_screen.dart` | `PhotoGridScreen` | 通用照片网格 | 改通用网格 |
| `screens/photo_preview_screen.dart` | `PhotoPreviewScreen` | 大图查看 + 信息 + **下载原图** | 改大图查看页 |
| `screens/upload_screen.dart` | `UploadScreen` + `_pickFiles()` | 选文件并上传到 PC | 改上传页 |
| `screens/settings_screen.dart` | `SettingsScreen` | 主题 + 设备信息 + 断开 | 改设置页 |
| `services/api_client.dart` | `ApiClient` | **所有 PC 端 API 调用** | 改/加移动端 API |
| `services/api_client.dart` | `getFileUrl` / `getPreviewUrl` / `getThumbnailUrl` | URL 构造器 | 改 URL 拼接 |
| `services/mdns_discovery.dart` | `MdnsDiscovery` + `DiscoveredService` | mDNS 客户端 | 改发现 |
| `services/device_info_service.dart` | `DeviceInfoService.getDeviceName()` | 跨平台设备名 | 改设备名 |
| `services/theme_provider.dart` | `ThemeProvider` | 主题状态 | 改主题逻辑 |
| `models/photo.dart` | `Photo` | 照片数据 | 改 photo 模型 |
| `models/photo_section.dart` | `PhotoSection` | 月份段（无照片） | — |
| `models/photo_section_with_photos.dart` | `PhotoSectionWithPhotos` | 月份段（含照片） | — |
| `models/folder_entry.dart` | `FolderEntry` | 文件夹 | — |
| `models/album_tree.dart` | `AlbumTree` | 树 | — |
| `models/upload_item.dart` | `UploadItem` | 待上传项 | — |
| `widgets/blur_arc_logo.dart` | `BlurArcLogo` | Logo SVG | 改 logo |
| `widgets/bottom_tab_bar.dart` | — | 底部 Tab（手机） | 改底部 Tab |
| `widgets/tablet_sidebar.dart` | — | 侧边栏（平板） | 改侧边栏 |
| `widgets/month_calendar_sheet.dart` | — | 月份跳转日历 | 改日历 |
| `widgets/photo_card.dart` | — | 照片卡片（移动端） | 改卡片 |
| `widgets/responsive_layout.dart` | — | 响应式布局工具 | 改布局判断 |
| `widgets/step_indicator.dart` | — | 连接步骤指示器 | 改步骤 |
| `widgets/tree_view.dart` | — | 树视图 | 改树 |
| `widgets/upload_progress.dart` | — | 上传进度条 | 改上传条 |
| `theme/app_theme.dart` | — | 主题样式（light/dark） | 改主题 |
| `theme/colors.dart` | — | 调色板 | 改色板 |

### Flutter App 启动链

```
main.dart::main()
  └─ BlurArcApp (MaterialApp)
     └─ home: 根 Provider 链
        ├─ ThemeProvider  (theme 切换)
        └─ home: 启动判断
           ├─ 未配对 → ConnectScreen
           └─ 已配对 → HomePage (Tab/Sidebar)
              ├─ AlbumScreen    (默认 Tab)
              ├─ FolderScreen
              ├─ MonthPhotoScreen
              ├─ UploadScreen
              └─ SettingsScreen
```

### Flutter App 关键数据流

```
[连接]
ConnectScreen → mDNS 发现 DiscoveredService
  → ApiClient.pairingRequest(deviceName)        POST /api/mobile/pairing/request
  → 跳 PairingCodeScreen（输入配对码）
  → ApiClient.pairingSubmitCode(code)           POST /api/mobile/pairing/submit-code
  → PC 端确认后 → ApiClient 用 token 拉数据
  → 跳 HomePage

[浏览]
AlbumScreen → ApiClient.getPhotoSections()      GET /api/mobile/photos/sections
            → ApiClient.getPhotosByMonth()      GET /api/mobile/photos/by-month
  → 点开 PhotoPreviewScreen
     → 显示 widget.api.getPreviewUrl(path)     GET /api/mobile/preview
     → 下载按钮 widget.api.getFileUrl(path)     GET /api/mobile/file → 本地 Download

[上传]
UploadScreen → _pickFiles() (image_picker.pickMultiImage)
  → ApiClient.upload(file)                      POST /api/mobile/upload
```

---

## 🔧 常见修改速查

| 想改 | 去这里 |
|------|--------|
| 加一个 PC 端 API | `backend/api_server.py`（在末尾 `@app.route` 区加路由 + 函数） |
| 加一个移动端 API | `backend/mobile_access_server.py`（在 `MobileAccessServer._register_routes` 内） |
| 改导入去重逻辑 | `backend/import_manager.py::ImportManager._import_file()` [L535] 和 `_do_import()` [L251] |
| 改缩略图大小/质量 | `backend/thumbnail_manager.py::ThumbnailManager` + `backend/constants.py` |
| 改 PC 端首页布局 | `frontend/src/App.tsx` + `components/layout/MainContent.tsx` |
| 改 PC 端导入弹窗 | `frontend/src/components/dialogs/ImportDialog/ImportDialog.tsx` |
| 改移动端首页 | `blurarc_app/lib/screens/album_screen.dart` |
| 改移动端大图查看 | `blurarc_app/lib/screens/photo_preview_screen.dart` |
| 改移动端上传 | `blurarc_app/lib/screens/upload_screen.dart` + `services/api_client.dart` |
| 改移动端连接页 | `blurarc_app/lib/screens/connect_screen.dart` |
| 改移动端设置 | `blurarc_app/lib/screens/settings_screen.dart` |
| 改移动端主题/颜色 | `blurarc_app/lib/theme/app_theme.dart` + `theme/colors.dart` |
| 改 mDNS 广播 | `backend/zeroconf_publisher.py` + `BlurArc.py::_start_mobile_service()` |
| 改启动菜单 | `scripts/dev-start.bat` |
| 改打包配置 | `BlurArc.spec` |
| 改数据库表 | `backend/database.py`（**注意迁移**） |
| 改默认端口/路径 | `backend/constants.py` |

---

## 🧪 测试

| 套件 | 入口 |
|------|------|
| 后端单元测试 | `test/unit/` （pytest） |
| 后端 API 集成测试 | `test/api/` |
| 移动端 | `blurarc_app/test/` （flutter test） |

```bash
# 后端
pytest                              # 全部
pytest test/unit/ -v                # 仅单元
pytest test/api/test_api_import_pytest.py   # 单文件

# 移动端
cd blurarc_app && flutter test
cd blurarc_app && flutter analyze
```

---

## 📝 文档目录

| 路径 | 内容 |
|------|------|
| `docs/devlogs/` | 按日期的 devlog（YYYY-MM-DD-topic.md） |
| `docs/plans/` | 计划/调研报告 |
| `docs/superpowers/specs/` | 设计方案 |
| `docs/prototypes/` | UI 原型（mobile/、tablet/、_compare/） |
| `docs/CODE_MAP.md` | **本文件** |
| `docs/API_REFERENCE.md` | PC 端 API 文档 |
| `docs/DATABASE_SCHEMA.md` | 数据库表结构 |
| `docs/DEVELOPMENT_GUIDE.md` | 开发指南 |
| `docs/GETTING_STARTED.md` / `QUICK_START.md` | 入门 |

---

## ⚠️ 修改前必读

- **改 UI 前**：先在 `docs/prototypes/` 对应平台目录写 HTML 原型，确认后再改代码
- **改前端代码后**：`cd frontend && npm run build`，否则 `python src/BlurArc.py` 加载的是旧 dist
- **改 Flutter 跨端代码后**：热更新跑模拟器按 `r`；真机重装
- **修改 `ImportManager._import_file()` 时**：注意 `md5_cache` 参数传递
- **mDNS `ServiceInfo` 参数顺序**：`port` 必须在 `addresses` 之前（zeroconf 0.132+）
- **方案/设计阶段不 commit**：设计文档写好确认后再一次性提交
