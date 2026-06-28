# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Blur Arc 是一个本地照片管理器，使用 PyWebView + Flask 构建，支持按 EXIF 日期自动整理、MD5 去重、视频缩略图等功能。

## 常用命令

```bash
# 构建前端并启动应用
cd frontend && npm run build && cd .. && python src/BlurArc.py

# 仅启动应用（前端未修改时）
python src/BlurArc.py

# 使用开发脚本启动后端
.\scripts\dev-start.ps1 backend

# 查看后端日志
.\scripts\dev-start.ps1 log

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

> **v0.7 起所有用户数据统一放在 `~/Documents/BlurArc/`**，升级/卸载只动 exe 目录。

- 相册目录：用户选择，媒体文件按 `YYYY/YYYY-MM/` 组织
- 数据库：`~/Documents/BlurArc/.config/photo_manager.db`（v0.7 改；v0.6 在 exe 目录）
- 缩略图缓存：`~/Documents/BlurArc/thumbnails/`（v0.7 改；v0.6 在 `~/.photomanager/`）
- 通用缓存：`~/Documents/BlurArc/cache/`（v0.7 新增；视频预览帧等）
- 用户配置：`~/Documents/BlurArc/.config/config.json`（v0.7 改；v0.6 在 `~/.photo_organizer_config.json`）
- 手机上传：`~/Documents/BlurArc/.config/phone_upload/`
- 手机配对 token：`~/Documents/BlurArc/.config/mobile_tokens.json`
- 应用日志：`~/Documents/BlurArc/logs/`
- 导出文件：`~/Documents/BlurArc/exports/`（v0.8+）
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
- **修改前端代码后必须先 `cd frontend && npm run build` 再启动应用**，否则浏览器加载的是旧的 dist 构建
- 修改 `_import_file()` 时需注意 `md5_cache` 参数传递

## 工作约定

- **方案/设计阶段不提交 git**：讨论和修改 spec 文档时只写文件，不 commit。等方案最终确认后一次性提交。实现阶段正常提交。
- 设计方案文档放在 `docs/superpowers/specs/` 目录下。
- **UI 修改必须先设计原型**：任何 UI 变更，先在 `docs/prototypes/` 目录下用 HTML 设计原型，确认后再实施代码。原型按 `docs/prototypes/<platform>/<feature>-v<version>[-<theme>].html` 命名，详见 `docs/prototypes/README.md`。
- **AI 编程必须遵守 `docs/AI-RULES.md`**：实施任何功能/修 bug 前，**先读 [docs/AI-RULES.md](docs/AI-RULES.md)**，按 §1 流程输出"影响面分析 + 反例清单 + 分步验证"三件套，再开始改代码。规则每次踩坑后追加。

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

### 国际化（i18n）

- **所有面向用户的文案必须通过 `useI18n().t('key')` 输出**，禁止在 TSX/TS 中硬编码中文或英文。
- 新增文案时，同步在 `frontend/src/contexts/I18nContext.tsx` 的 `zh` 和 `en` 两个字典中添加 key。
- key 命名采用 `模块.语义` 风格，例如 `settings.rebuildComplete`、`app.loadFavoritesFailed`。
- 后端返回给前端展示的状态/进度消息，应返回 i18n key（如 `rebuild.scanning`），由前端根据当前语言渲染；避免后端直接返回人类可读的中文或英文字符串。
- 复用已有 key，避免重复定义同义文案。

## Flutter App 开发

Flutter App 位于 `blurarc_app/` 目录，用于手机/平板通过局域网浏览相册和推送照片。

```bash
cd blurarc_app

# 安装依赖（首次）
flutter pub get

# 代码分析
flutter analyze

# 运行（需要连接 Android 真机或模拟器）
flutter run

# 构建 APK
flutter build apk
```

**Flutter SDK 位置：** `E:\Applications\flutter`（已添加到用户 PATH）

**注意：** `blurarc_app/` 包含完整的 android/ios 平台目录，可通过 `flutter run` 直接编译运行。手机/模拟器部署可使用 `.\scripts\dev-start.bat` 或 `.\scripts\dev-start.ps1 phone`。

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

## 🗺️ 代码地图

完整的模块/入口/调用链速查表（按功能找文件）见 [docs/CODE_MAP.md](docs/CODE_MAP.md)。
**改任何功能前先查这张表**。

---

## 📋 开发日志

开发日志存放在 `docs/devlogs/` 目录，按 `YYYY-MM-DD-<topic>.md` 命名。
每次实质性开发完成后自动新增或更新对应日志文件。查阅时直接读取该目录下列表即可。

| 日期 | 主题 | 文件 |
|------|------|------|
| 2026-06-27 | 相册默认封面拍立得堆叠设计 + 公共组件化 | [devlog](docs/devlogs/2026-06-27-album-cover-default.md) |
| 2026-06-27 | Timeline 对齐 Apple Photos（3 tab + 双击导航） | [devlog](docs/devlogs/2026-06-27-timeline-apple-photos-refactor.md) |
| 2026-06-22 | mDNS 广播修复（ServiceInfo 参数顺序 + 自动启动） | [devlog](docs/devlogs/2026-06-22-mdns-broadcast-fix.md) |
| 2026-06-22 | 导入预检目标重复检测性能修复（删除 rglob 兜底） | [devlog](docs/devlogs/2026-06-22-import-target-dedup-perf.md) |
| 2026-06-22 | 手机端首次连接照片加载卡死修复（Dio sendTimeout + SQL 索引） | [devlog](docs/devlogs/2026-06-22-mobile-first-load-fix.md) |
| 2026-06-21 | 移动接入 Bug 修复 + 上传通知导入 | [devlog](docs/devlogs/2026-06-21-upload-bug-fixes.md) |
| 2026-06-20 | 移动端 4 个 Bug 排查报告 | [plan](docs/plans/2026-06-20-mobile-bugs-analysis.md) |
| 2026-06-19 | Flutter mDNS 自动发现实现 | [devlog](docs/devlogs/2026-06-19-mdns-discovery.md) |
| 2026-06-19 | 移动端 UI 重设计技术实现方案 | [spec](docs/superpowers/specs/2026-06-19-mobile-ui-redesign.md) |
| 2026-06-19 | 原型 Logo SVG 统一管理 + 手机 App 实施计划 | [devlog](docs/devlogs/2026-06-19-prototype-logo-plan.md) |
| 2026-06-19 | 移动端 UI 重设计实施（7 Phase 完成） | [devlog](.workbuddy/memory/2026-06-19.md) |
| 2026-06-18 | 移动接入功能（手机上传、配对流程） | [devlog](docs/devlogs/2026-06-18-mobile-access.md) |

---

## 🧠 通用编码准则

> 来源：[Andrej Karpathy 的 LLM 编码准则](https://github.com/forrestchang/andrej-karpathy-skills/blob/main/CLAUDE.md)
> 与项目特定规则合并使用。**权衡：** 这些准则偏向谨慎而非速度，对琐碎任务可自行判断。

### 1. 编码前先思考

**不要假设。不要掩饰困惑。主动暴露权衡。**

实施前：
- 明确陈述假设。不确定就问。
- 存在多种解释时，全部呈现 —— 不要默默选一个。
- 有更简单的方案时，直说。必要时反驳。
- 有不清楚的地方，停下。指出困惑点。问。

### 2. 简单优先

**用最少的代码解决问题。不做投机性设计。**

- 不实现需求之外的功能。
- 不为一次性代码做抽象。
- 不做未要求的"灵活性"或"可配置性"。
- 不为不可能发生的场景做错误处理。
- 如果写了 200 行但 50 行就够，重写。

自问："资深工程师会不会觉得这过度复杂？" 会的话，简化。

### 3. 手术式修改

**只动必须动的地方。只清理自己制造的混乱。**

修改现有代码时：
- 不要"顺手改进"相邻代码、注释或格式。
- 不要重构没坏的东西。
- 匹配现有风格，哪怕你会换种写法。
- 注意到无关的死代码，提一下 —— 不要删。

你的修改产生孤儿时：
- 移除因**你的改动**而变得未使用的 import/变量/函数。
- 不要移除预先存在的死代码，除非被要求。

检验标准：每一行改动都能直接追溯到用户请求。

### 4. 目标驱动执行

**定义成功标准。循环验证直到通过。**

把任务转化为可验证目标：
- "加校验" → "为非法输入写测试，然后让它们通过"
- "修 bug" → "写一个能复现 bug 的测试，然后让它通过"
- "重构 X" → "确保前后测试都通过"

多步任务，给出简短计划：
```
1. [步骤] → 验证：[检查点]
2. [步骤] → 验证：[检查点]
3. [步骤] → 验证：[检查点]
```

强成功标准让你独立循环。弱标准（"让它能跑"）需要不断澄清。

---

**这些准则起作用的标志：** diff 里不必要的改动更少、因过度复杂而重写更少、澄清问题出现在实施之前而非犯错之后。

