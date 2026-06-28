<p align="center">
  <img src="https://img.shields.io/badge/版本-v0.7.0-gold?style=flat-square" />
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

## 核心功能

### 智能归档

- **EXIF 日期读取**：自动从照片/视频提取拍摄时间
- **按日期归档**：整理至 `YYYY/YYYY-MM/` 目录结构
- **原子计数器命名**：同秒连拍自动编号（`20240315_143022_001.jpg`）
- **重复文件处理**：加 `_dup` 后缀保留，供用户手动审查

### 高效导入

- **两阶段去重**：文件大小预筛 + MD5 精确比对，减少 99% 无效 I/O
- **可暂停导入**：多线程并行，实时进度，随时暂停/继续/取消
- **复制/移动模式**：导入时选择保留源文件或移动导入
- **HEIC/HEIF/AVIF 支持**：magic bytes 检测，iPhone 照片不丢日期
- **10K 文件导入优化**：600s → ~140s（节省 77%）

### 浏览体验

- **时间线视图**：按年/月/日分组浏览，Apple Photos 风格
- **文件夹树浏览**：侧边栏目录树，展开/折叠，快速导航
- **相册管理**：创建/编辑/删除相册，照片可加入多个相册
- **收藏功能**：一键收藏照片，快速访问收藏列表
- **批量选择**：多选删除、批量操作，支持全选/反选
- **缩放控制**：3 级缩放（小/中/大），适应不同屏幕
- **暗/亮主题**：跟随系统或手动切换，统一视觉风格

### 视频支持

- **FFmpeg 集成**：视频缩略图生成、元数据提取
- **HTTP Range 播放**：支持任意 Seek，拖拽进度条
- **自动提取信息**：时长、分辨率、编码信息
- **原生播放**：浏览器内直接播放，无需外部播放器

### 全格式预览

- **支持格式**：JPG / PNG / HEIC / TIFF / BMP / RAW / WEBP / GIF
- **自动转换**：HEIC / TIFF / BMP / ICO 自动转 JPEG 缩略图
- **视频预览**：MP4 / MOV / AVI / MKV 等主流格式
- **错误占位图**：缩略图加载失败显示友好提示

### 手机互联

- **Flutter 移动端 App**：支持 Android / iOS / 平板
- **局域网浏览**：手机无线浏览 PC 端相册，流畅滚动
- **推送照片**：手机选图推送到 PC，自动归档到 `YYYY/YYYY-MM/`
- **mDNS 自动发现**：PC 启动自动广播，手机自动发现，无需手输 IP
- **安全配对**：6 位配对码 + Token 鉴权，避免二维码扫描失败
- **上传闭环**：手机推送 → PC 自动归档 → 弹窗通知 → 一键导入

### 其他功能

- **右键菜单**：预览 / 打开文件 / 删除 / 打开资源管理器
- **预览翻页**：← → 键翻页，显示「3/12」索引徽标
- **Toast 通知**：操作反馈右下角滑入动画，不打断操作流
- **统计信息**：照片数/视频数/时间跨度
- **导出功能**：批量导出照片到指定目录
- **索引重建**：支持增量/全量重建索引，保留收藏状态

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
│   ├── mobile_access_server.py    # 移动接入服务（独立端口）
│   ├── zeroconf_publisher.py      # mDNS 局域网广播
│   ├── import_manager.py          # 异步导入 + 两阶段去重
│   ├── thumbnail_manager.py       # 缩略图生成与缓存
│   ├── video_processor.py         # FFmpeg 视频处理
│   ├── database.py                # 数据模型
│   └── config_manager.py          # 配置管理 + 索引重建
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
- **mDNS 自动发现**：手机打开 App 即可看到同一局域网内的 PC
- **安全配对**：PC 端弹 6 位配对码 + Token 鉴权
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

## 开发

```bash
# 后端
pip install -r requirements.txt
python src/BlurArc.py

# 前端开发模式
cd frontend
npm install
npm run dev

# 前端构建
cd frontend
npm run build
```

## 许可证

[MIT](LICENSE) &copy; 2026
