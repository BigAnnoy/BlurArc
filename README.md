<p align="center">
  <img src="https://img.shields.io/badge/版本-v0.5.1-gold?style=flat-square" />
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/平台-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" />
  <img src="https://img.shields.io/badge/许可证-MIT-lightgrey?style=flat-square" />
</p>

<p align="center">
  让照片回归秩序。<br/>
  完全本地运行，隐私零泄露，无任何云端依赖。
</p>

---

## 为什么选择 Blur Arc

市面上的照片管理工具要么依赖云端、要么停止维护。Blur Arc 是一个**完全本地**的照片/视频管理器——数据不离机，按拍摄日期自动归档，导入时智能去重。

## 核心能力

| | |
|---|---|
| **智能归档** | 读取 EXIF 拍摄时间，自动整理至 `YYYY/YYYY-MM/` 目录 |
| **高效去重** | 文件大小预筛 + MD5 精确比对，减少 99% 无效 I/O |
| **可暂停导入** | 多线程并行，实时进度，随时暂停/继续/取消 |
| **视频支持** | FFmpeg 集成，HTTP Range 拖拽播放，自动提取时长与编码信息 |
| **全格式预览** | HEIC / TIFF / BMP / RAW 自动转 JPEG 缩略图 |
| **批量操作** | 多选删除、复制/移动导入、右键菜单、键盘快捷键 |

## 快速开始

### 下载运行

前往 [Releases](https://github.com/BigAnnoy/BlurArc/releases) 下载 `BlurArc.exe`，双击即可运行。

### 从源码启动

```bash
git clone https://github.com/BigAnnoy/BlurArc.git
cd BlurArc
pip install -r requirements.txt
python src/BlurArc.py
```

首次启动会引导选择相册存储目录。

### FFmpeg（可选）

视频缩略图和元数据提取需要 FFmpeg，未安装时图片功能完全正常。

```bash
python scripts/download_ffmpeg.py
```

自动下载静态编译版到 `backend/ffmpeg_binaries/`，无需手动配置。

## 技术栈

| 层 | 技术 |
|---|---|
| 窗口 | PyWebView 6.1+ |
| 后端 | Flask 2.3+ / SQLAlchemy / SQLite |
| 前端 | React 19 / TypeScript / Vite / Tailwind CSS |
| 图像 | Pillow / pillow-heif |
| 视频 | FFmpeg 8.1.1 |

## 项目结构

```
BlurArc/
├── src/BlurArc.py                 # 主入口
├── backend/
│   ├── api_server.py              # REST API（35+ 端点）
│   ├── import_manager.py          # 异步导入 + 两阶段去重
│   ├── thumbnail_manager.py       # 缩略图生成与缓存
│   ├── video_processor.py         # FFmpeg 视频处理
│   ├── database.py                # 数据模型
│   └── config_manager.py          # 配置管理
├── frontend/                      # React + TypeScript 前端
├── docs/                          # 文档与落地页
├── scripts/                       # FFmpeg 下载、发布脚本
├── installer/                     # NSIS Windows 安装包
├── test/                          # 测试
├── BlurArc.spec                   # PyInstaller 打包
└── requirements.txt
```

整理后的相册目录结构：

```
相册/
└── 2024/
    └── 2024-03/
        ├── 20240315_143022_001.jpg
        ├── 20240315_143022_002.jpg   ← 同秒连拍自动序号
        └── 20240316_091500_001.mp4
```

## API 概览

```
GET  /api/health                    # 健康检查
GET  /api/album/stats               # 统计（照片数/视频数/时间跨度）
GET  /api/album/tree                # 目录树
GET  /api/album/photos?path=...     # 照片列表
GET  /api/album/thumbnail?path=...  # 缩略图
GET  /api/album/preview?path=...    # 特殊格式预览
POST /api/import/check              # 导入预检（去重 + 统计）
POST /api/import/start              # 启动异步导入
GET  /api/import/progress/<id>      # 实时进度
POST /api/import/pause/<id>         # 暂停
POST /api/import/resume/<id>        # 继续
POST /api/files/delete              # 批量删除
```

完整 API 文档见 [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

## 开发

```bash
# 后端
pip install -r requirements.txt
python src/BlurArc.py

# 前端开发模式
cd frontend
npm install
npm run dev
```

## 许可证

[MIT](LICENSE) &copy; 2026
