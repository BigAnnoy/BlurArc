# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

FrameAlbum 是一个本地照片管理器，使用 PyWebView + Flask 构建，支持按 EXIF 日期自动整理、MD5 去重、视频缩略图等功能。

## 常用命令

```bash
# 启动应用
python src/FrameAlbum.py

# 运行所有测试
pytest

# 运行单个测试文件
pytest test/test_app.py -v

# 运行单元测试
pytest -m unit

# 安装依赖
pip install -r requirements.txt

# 下载 FFmpeg（视频功能需要）
python scripts/download_ffmpeg.py
```

## 架构概览

### 后端 (Flask)

- `src/FrameAlbum.py` - 主入口，启动 Flask 服务器和 PyWebView 窗口
- `backend/api_server.py` - Flask REST API（25+ 端点），核心业务逻辑
- `backend/import_manager.py` - 异步导入逻辑，MD5 去重
- `backend/thumbnail_manager.py` - 缩略图生成与缓存
- `backend/video_processor.py` - FFmpeg 视频处理
- `backend/database.py` - SQLAlchemy 数据模型
- `backend/config_manager.py` - 配置管理

### 前端 (原生 JS)

- `frontend/index.html` - 单页应用入口
- `frontend/js/` - 主要 JS 文件（非模块化）
- `frontend/modules/` - ES 模块化 JS（api/, components/, utils/）

### 数据流

1. 前端通过 `/api/*` 调用后端
2. 导入流程：`/api/import/check` 预检 → `/api/import/start` 启动 → `/api/import/progress` 轮询进度
3. 去重策略：(文件大小 + EXIF 时间) 预筛 → MD5 精确比对

### 路径约定

- 相册目录：用户选择，媒体文件按 `YYYY/YYYY-MM/` 组织
- 缩略图缓存：`相册目录/.thumbnails/`
- MD5 记录：`相册目录/.photo_organizer.json`
- 用户配置：`~/.photo_organizer_config.json`

## 关键注意事项

- 前端有两套 JS：`frontend/js/`（全局脚本）和 `frontend/modules/`（ES 模块），修改时需同步
- 视频功能依赖 FFmpeg，未安装时图片功能仍正常
- 打包使用 PyInstaller，配置在 `FrameAlbum.spec`
