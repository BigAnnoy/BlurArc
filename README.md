<p align="center">
  <img src="https://img.shields.io/badge/版本-v0.6.0-gold?style=flat-square" />
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/平台-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" />
  <img src="https://img.shields.io/badge/许可证-MIT-lightgrey?style=flat-square" />
</p>

<p align="center">
  <img src="docs/badges/coverage-backend.svg" alt="Backend Coverage" />
  <img src="docs/badges/coverage-frontend.svg" alt="Frontend Coverage" />
  <img src="docs/badges/coverage-flutter.svg" alt="Flutter Coverage" />
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
| **手机互联** | Flutter 移动端 App，局域网无线浏览相册、推送照片（mDNS 发现 + 安全配对） |
| **自动配对** | PC 端弹 6 位配对码 + Token 鉴权，避免二维码扫描失败 |
| **mDNS 零配置** | PC 启动自动广播 `_blurarc._tcp.local.`，手机自动发现，无需手输 IP |
| **跨设备适配** | 同一份代码适配手机竖屏 / 平板横屏 / 桌面 PC，统一暗/亮主题 |
| **上传闭环** | 手机选图推送 → PC 自动归档 → ImportDialog 弹窗通知 → 一键导入 |

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
| 移动端 | Flutter 3.44+ (Android / iOS / 平板) |
| 图像 | Pillow / pillow-heif |
| 视频 | FFmpeg 8.1.1 |
| 局域网发现 | Zeroconf (mDNS) |

## 项目结构

```
BlurArc/
├── src/BlurArc.py                 # 主入口
├── backend/
│   ├── api_server.py              # REST API（35+ 端点）
│   ├── mobile_access_server.py     # 移动接入服务（独立端口）
│   ├── zeroconf_publisher.py     # mDNS 局域网广播
│   ├── import_manager.py          # 异步导入 + 两阶段去重
│   ├── thumbnail_manager.py       # 缩略图生成与缓存
│   ├── video_processor.py         # FFmpeg 视频处理
│   ├── database.py                # 数据模型
│   └── config_manager.py          # 配置管理
├── frontend/                      # React + TypeScript 前端
├── blurarc_app/                   # Flutter 移动端 App
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

## 移动端 App

Blur Arc 提供 Flutter 移动端伴侣 App（[blurarc_app/](blurarc_app/)），支持 **Android** / **iOS** 手机与平板。

### 主要能力

- **浏览相册**：按月份分组的照片墙，流畅滚动，缩略图 → 中等预览 → 一键下载原图
- **推送照片**：手机相册批量选图，上传到 PC 端自动归档到 `YYYY/YYYY-MM/`
- **mDNS 自动发现**：手机打开 App 即可看到同一局域网内的 PC（`_blurarc._tcp.local.`）
- **安全配对**：PC 端弹 6 位配对码 + Token 鉴权，避免二维码扫描失败
- **跨设备适配**：手机竖屏、平板横屏自动切换布局，统一暗/亮主题

### 启动流程

```
PC 端：python src/BlurArc.py    →  自动开启移动接入服务 + mDNS 广播
        ↓
手机端：flutter run              →  mDNS 发现 PC 列表
        ↓ 点 PC  →  输入 6 位配对码  →  PC 端确认  →  配对成功
        ↓
开始浏览 / 上传
```

### 移动端相关端点

```
POST /api/mobile/pairing/request         # 发起配对
POST /api/mobile/pairing/submit-code     # 提交配对码
GET  /api/mobile/photos/sections         # 月份分组
GET  /api/mobile/photos/by-month?ym=...  # 单月照片
GET  /api/mobile/thumbnail?path=...      # 缩略图（带 Token）
GET  /api/mobile/file?path=...           # 原图（带 Token）
GET  /api/mobile/preview?path=...        # 中等预览
POST /api/mobile/upload                  # 上传文件
POST /api/mobile/upload/done             # 通知 PC 端有上传完成
```

完整移动端 API 与 PC 端 API 文档见 [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

### 约束

- **Android 模拟器不支持 mDNS**（NAT 隔离组播），自动发现只能在真机测试；模拟器需手动输入 `10.0.2.2:8900`
- App 内部版本 `1.0` 与 PC 端 `v0.5.3` 解耦

---

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
GET  /api/mobile/status             # 移动接入开关
POST /api/mobile/pairing/start      # PC 端发起配对（弹配对码）
GET  /api/mobile/pairing/pending    # 等待手机输入的配对码
POST /api/mobile/pairing/confirm    # PC 端确认
GET  /api/mobile/devices            # 已配对设备列表
POST /api/mobile/revoke             # 撤销单台设备
POST /api/mobile/upload/done        # 移动端通知上传完成（弹 ImportDialog）
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
