# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## 项目概述

Blur Arc 是一个本地照片管理器，使用 PyWebView + Flask 构建，支持按 EXIF 日期自动整理、MD5 去重、视频缩略图等功能。

## 常用命令

```bash
# 启动应用
python src/BlurArc.py

# 运行所有测试
pytest

# 运行单元测试
pytest test/unit/ -v

# 安装依赖
pip install -r requirements.txt

# 下载 FFmpeg（视频功能需要）
python scripts/download_ffmpeg.py
```

## 架构概览

### 后端 (Flask)

- `src/BlurArc.py` - 主入口，启动 Flask 服务器和 PyWebView 窗口
- `backend/api_server.py` - Flask REST API（25+ 端点），核心业务逻辑
- `backend/import_manager.py` - 异步导入逻辑，MD5 去重（两阶段预筛 + 并行计算）
- `backend/thumbnail_manager.py` - 缩略图生成与缓存
- `backend/video_processor.py` - FFmpeg 视频处理（已集成 8.1.1）
- `backend/database.py` - SQLAlchemy 数据模型
- `backend/config_manager.py` - 配置管理
- `backend/utils.py` - 工具函数（MD5 计算、文件指纹）
- `backend/ffmpeg_binaries/` - FFmpeg 二进制文件

### 前端 (React + TypeScript)

- `frontend/src/App.tsx` - 主应用组件
- `frontend/src/components/` - UI 组件
  - `common/` - 通用组件
  - `dialogs/` - 对话框组件
  - `layout/` - 布局组件
  - `photos/` - 照片相关组件
  - `sidebar/` - 侧边栏组件
- `frontend/src/services/api.ts` - API 服务
- `frontend/src/hooks/` - 自定义 Hooks
- `frontend/src/stores/` - 状态管理
- `frontend/src/types/` - TypeScript 类型定义
- `frontend/src/utils/` - 工具函数

### 数据流

1. 前端通过 `/api/*` 调用后端
2. 导入流程：`/api/import/check` 预检 → `/api/import/start` 启动 → `/api/import/progress` 轮询进度
3. 去重策略：**两阶段预筛** → 文件大小分组 → 只对大小相同的组计算 MD5

### 性能优化

| 优化项 | 实现方式 |
|--------|----------|
| MD5 缓存复用 | `md5_cache` 字典，一次导入只算一次 |
| 并行源去重 | `ThreadPoolExecutor` 并行计算 |
| 两阶段预筛 | 按文件大小分组，跳过不可能重复的文件 |

### 路径约定

- 相册目录：用户选择，媒体文件按 `YYYY/YYYY-MM/` 组织
- 数据库：`项目根目录/.config/photo_manager.db`（开发模式）或 `exe所在目录/.config/`（打包模式）
- 缩略图缓存：`~/.photomanager/thumbnails/`（用户主目录，跨相册共享）
- MD5 记录：存储在 SQLite 数据库
- 用户配置：`~/.photo_organizer_config.json`
- FFmpeg：`backend/ffmpeg_binaries/ffmpeg.exe`

## 功能说明

### 照片选择与删除

工具栏提供批量选择删除功能：

| 模式 | 按钮 | 行为 |
|------|------|------|
| 正常模式 | `[选择]` | 点击进入选择模式 |
| 选择模式 | `[取消]` `[全选]` `[删除]` | 点击照片选中/取消，支持全选 |

**交互细节：**
- 选中照片显示蓝色边框 + 左上角勾选图标
- 标题栏显示"已选 N 张"
- 删除按钮在未选中时禁用
- 全选后按钮变为"取消全选"

**相关组件：**
- `MainContent.tsx` - 工具栏按钮
- `PhotoCard.tsx` - 选中状态样式
- `PhotoGrid.tsx` - 传递选中状态
- `App.tsx` - `selectionMode`/`selectedIds` 状态管理

## 关键注意事项

- 前端使用 React 19 + TypeScript + Vite + Tailwind CSS，开发时运行 `npm run dev`
- FFmpeg 已集成到 `backend/ffmpeg_binaries/`，视频功能开箱即用
- 打包使用 PyInstaller，配置在 `BlurArc.spec`
- 修改 `_import_file()` 时需注意 `md5_cache` 参数传递
- **UI 修改必须先设计原型**：任何 UI 变更，先在 `docs/prototypes/` 目录下用 HTML 设计原型，确认后再实施代码。详见 `docs/prototypes/README.md`。

## 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

## Flutter App 开发

Flutter App 位于 `blurarc_app/` 目录，用于手机/平板通过局域网浏览相册和推送照片。

```bash
cd blurarc_app

# 安装依赖
flutter pub get

# 代码分析
flutter analyze

# 运行（需要连接 Android 真机或模拟器）
flutter run

# 构建 APK
flutter build apk
```

**Flutter SDK 位置：** `E:\Applications\flutter`（已添加到用户 PATH）

## mDNS 广播注意事项

**依赖版本：** 后端 `zeroconf>=0.132.0`（当前 0.149.16），Flutter 端 `multicast_dns: ^0.3.2`

**`ServiceInfo` 参数顺序陷阱：** `zeroconf` 0.132+ 中 `addresses` 是 keyword-only 参数，**不能作为位置参数传递**。错误写法会导致 `TypeError: multiple values for 'port'`，线程静默失败：

```python
# ❌ 错误 — addresses 被当作 port 参数
ServiceInfo(SERVICE_TYPE, name, addresses=[...], port=self.port, ...)

# ✅ 正确 — port 先于 addresses
ServiceInfo(SERVICE_TYPE, name, port=self.port, addresses=[...], ...)
```

**调用链：** `BlurArc.py: _start_mobile_service()` → `server.start()` → `server.start_pairing_mode()` → `ZeroconfPublisher.start()` → 后台线程注册 `_blurarc._tcp.local.`

**调试：** `ZeroconfPublisher.wait_ready(timeout)` 可确认广播是否成功启动，`_last_error` 可查看错误原因。

**限制：** Android 模拟器不支持组播（NAT 隔离），mDNS 自动发现只能在真机测试。模拟器手动输入 `10.0.2.2:8900`。

---

## 📋 开发日志

开发日志存放在 `docs/devlogs/` 目录，按 `YYYY-MM-DD-<topic>.md` 命名。
每次实质性开发完成后自动新增或更新对应日志文件。查阅时直接读取该目录下列表即可。

| 日期 | 主题 | 文件 |
|------|------|------|
| 2026-06-22 | mDNS 广播修复（ServiceInfo 参数顺序 + 自动启动） | [devlog](docs/devlogs/2026-06-22-mdns-broadcast-fix.md) |
| 2026-06-22 | 导入预检目标重复检测性能修复（删除 rglob 兜底） | [devlog](docs/devlogs/2026-06-22-import-target-dedup-perf.md) |
| 2026-06-22 | 手机端首次连接照片加载卡死修复（Dio sendTimeout + SQL 索引） | [devlog](docs/devlogs/2026-06-22-mobile-first-load-fix.md) |
| 2026-06-21 | 移动端 4 Bug 修复（上传Tab/图片401/配对码输入框/错误提示） | [devlog](.workbuddy/memory/2026-06-21.md) |
| 2026-06-20 | 移动端 4 个 Bug 排查报告 | [plan](docs/plans/2026-06-20-mobile-bugs-analysis.md) |
| 2026-06-19 | Flutter mDNS 自动发现实现 | [devlog](docs/devlogs/2026-06-19-mdns-discovery.md) |
| 2026-06-19 | 移动端 UI 重设计技术实现方案 | [spec](docs/superpowers/specs/2026-06-19-mobile-ui-redesign.md) |
| 2026-06-19 | 原型 Logo SVG 统一管理 + 手机 App 实施计划 | [devlog](docs/devlogs/2026-06-19-prototype-logo-plan.md) |
| 2026-06-19 | 移动端 UI 重设计实施（7 Phase 完成） | [devlog](.workbuddy/memory/2026-06-19.md) |
| 2026-06-18 | 移动接入功能（手机上传、配对流程） | [devlog](docs/devlogs/2026-06-18-mobile-access.md) |
