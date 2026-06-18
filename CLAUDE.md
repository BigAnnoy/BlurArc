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
- **修改前端代码后必须先 `cd frontend && npm run build` 再启动应用**，否则浏览器加载的是旧的 dist 构建
- 修改 `_import_file()` 时需注意 `md5_cache` 参数传递

## 工作约定

- **方案/设计阶段不提交 git**：讨论和修改 spec 文档时只写文件，不 commit。等方案最终确认后一次性提交。实现阶段正常提交。
- 设计方案文档放在 `docs/superpowers/specs/` 目录下。

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
