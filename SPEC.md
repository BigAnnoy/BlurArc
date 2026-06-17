# Blur Arc v0.5 产品规格说明书

## 1. 项目概述

| 属性 | 详情 |
|------|------|
| **项目名称** | Blur Arc |
| **版本** | v0.5.0 |
| **类型** | 本地照片/视频管理器（桌面应用） |
| **许可证** | MIT |
| **平台** | Windows / macOS / Linux |
| **核心功能** | 相册管理、照片导入、缩略图缓存、EXIF 查看、视频预览 |
| **目标用户** | 希望整理和浏览本地照片/视频的普通用户 |

---

## 2. 核心功能

### 2.1 相册管理
- 选择本地文件夹作为相册根目录
- 递归遍历目录树，按年月结构展示媒体文件
- 支持按日期、文件类型筛选
- 照片网格视图，支持缩略图大图预览
- 右键菜单：打开文件、打开所在文件夹、删除

### 2.2 照片导入
- 选择源文件夹，扫描支持格式（jpg/jpeg/png/heic/webp/bmp/gif/tiff/mp4/mov/avi 等）
- **两阶段去重**：
  1. 预筛：`size + EXIF 时间` 相同的文件标记为候选
  2. 精确匹配：MD5 计算确认，相同则重命名加 `_dup` 后缀
- 支持"复制"或"剪切"两种导入模式
- 按拍摄日期自动分类：`YYYY/YYYY-MM/` 目录结构
- 支持暂停 / 继续 / 取消导入

### 2.3 缩略图缓存
- 基于 MD5（路径 + 修改时间 + 大小）的缓存键
- 缓存目录：`~/.photomanager/thumbnails/`
- LRU 淘汰策略：按访问时间自动清理超量缓存
- 支持 HEIC / TIFF / BMP / ICO → JPEG 预览转换

### 2.4 EXIF 信息
- 读取并展示：拍摄时间、相机品牌/型号、焦距、光圈、快门、ISO、GPS
- 优先从 EXIF 读取时间，缺失则使用文件修改时间

### 2.5 视频支持
- 视频缩略图（FFmpeg 提取第 1 秒帧）
- 视频元数据（时长、分辨率、编码格式）
- 浏览器 Range 请求支持视频拖动定位

---

## 3. 技术架构

```
┌─────────────────────────────────────────────┐
│                 PyWebView 窗口                │
│         (加载 http://127.0.0.1:5000)          │
│           Chromium WebView (暗色主题)         │
└────────────────────┬────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────┐
│             Flask API Server                │
│           backend/api_server.py             │
│         25+ REST endpoints (threaded)        │
└──┬──────────┬──────────┬───────────────────┘
   │          │          │
   ▼          ▼          ▼
import_  thumbnail_  config_    database.py
manager  manager     manager    (SQLAlchemy)
.py      .py         .py
   │          │
   ▼          ▼
video_     utils.py
processor  constants.py
.py

─────────────────────────────────────────────
│                 Frontend                    │
│    (ES Modules 新架构 + 传统全局 JS 双轨)     │
│  暗色主题 UI / 中英双语 / 响应式布局          │
└─────────────────────────────────────────────┘
```

### 3.1 技术栈

| 层级 | 技术 |
|------|------|
| 桌面窗口 | PyWebView 4.x（嵌入 Chromium WebView） |
| API 服务 | Flask 2.x + Flask-CORS（`http://127.0.0.1:5000`，threaded 模式） |
| 数据库 | SQLAlchemy 2.x + SQLite（`.config/photo_manager.db`） |
| 图像处理 | Pillow 9.x + pillow-heif（HEIC 格式支持） |
| 视频处理 | FFmpeg / ffprobe（可选，bundled 或 PATH） |
| 打包 | PyInstaller（`BlurArc.spec`） |
| 前端 | HTML5 + CSS3 + Vanilla JS（ES Modules 双轨制） |
| 国际化 | 中英双语（`js/i18n.js`） |

### 3.2 目录结构

```
e:/BlurArc/
├── src/
│   └── BlurArc.py              # 应用入口（PyWebView + Flask 集成）
├── backend/
│   ├── api_server.py              # Flask REST API（25+ 端点）
│   ├── import_manager.py          # 导入管理（ThreadPoolExecutor 多线程）
│   ├── thumbnail_manager.py       # 缩略图生成与缓存
│   ├── video_processor.py         # FFmpeg 视频处理封装
│   ├── config_manager.py          # 配置读写（JSON）
│   ├── database.py                 # SQLAlchemy ORM（6 张表）
│   ├── constants.py                # 媒体格式常量
│   ├── utils.py                   # MD5 计算等工具函数
│   └── ffmpeg_binaries/           # 捆绑的 FFmpeg（可选）
├── frontend/
│   ├── index.html                 # SPA 入口
│   ├── js/                        # 传统全局变量架构（主力）
│   │   ├── main.js                # 主逻辑（55KB）
│   │   ├── import-dialog.js      # 导入对话框（106KB）
│   │   ├── album-browser.js      # 相册浏览器（33KB）
│   │   ├── api.js                 # Fetch 封装
│   │   └── i18n.js                # 国际化
│   └── modules/                   # ES Modules 新架构（迁移中）
│       ├── api/                   # API 模块化封装
│       ├── components/             # 组件化 UI
│       └── compatibility.js        # 兼容层（旧全局变量桥接）
├── scripts/
│   └── download_ffmpeg.py          # FFmpeg 自动下载脚本
├── test/                          # pytest 单元测试
├── docs/                          # 图标等资源
├── BlurArc.spec                # PyInstaller 打包配置
├── requirements.txt                # 生产依赖
├── requirements-dev.txt           # 开发依赖
├── SPEC.md                        # 本规格文档
├── README.md                      # 项目说明
└── CHANGELOG.md                   # 版本变更记录
```

---

## 4. API 接口列表

### 4.1 健康检查
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 服务健康检查 |

### 4.2 相册
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/album/stats` | 相册统计（照片数/视频数/总大小） |
| GET | `/api/album/tree` | 目录树（迭代遍历） |
| GET | `/api/album/photos` | 照片列表（分页、排序） |
| GET | `/api/album/exif` | EXIF 元数据 |
| DELETE | `/api/album` | 删除相册 |

### 4.3 导入
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/import/check` | 预检源路径 |
| POST | `/api/import/start` | 开始导入 |
| GET | `/api/import/progress` | 获取进度 |
| POST | `/api/import/cancel` | 取消导入 |
| POST | `/api/import/pause` | 暂停导入 |
| POST | `/api/import/resume` | 继续导入 |

### 4.4 文件
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/files/info` | 文件信息 |
| DELETE | `/api/files/delete` | 删除文件 |
| POST | `/api/files/open` | 用系统默认应用打开 |

### 4.5 缩略图
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/thumbnail` | 获取缩略图（自动生成缓存） |

### 4.6 视频
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/video/metadata` | 视频元数据 |
| GET | `/api/video/stream` | 视频流（Range 请求） |

### 4.7 设置
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings/album-path` | 获取相册路径 |
| PUT | `/api/settings/album-path` | 设置相册路径 |
| GET | `/api/settings/config` | 获取完整配置 |
| POST | `/api/settings/config` | 更新配置 |

### 4.8 系统
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/system/info` | 系统信息 |
| POST | `/api/system/rebuild_md5` | 重建 MD5 索引 |
| GET | `/api/system/rebuild_progress` | 重建进度 |

### 4.9 缓存
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/cache/stats` | 缓存统计 |
| POST | `/api/cache/cleanup` | 清理缓存 |

---

## 5. 数据库设计

### 5.1 photos（照片记录表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| filename | VARCHAR(255) | 文件名 |
| path | VARCHAR(1024) | 完整路径 |
| size | INTEGER | 文件大小（字节） |
| md5_hash | VARCHAR(32) | MD5 值（无唯一约束，允许 _dup） |
| media_date | DATETIME | 媒体拍摄日期 |
| file_type | VARCHAR(16) | photo / video |
| extension | VARCHAR(16) | 扩展名 |
| imported_at | DATETIME | 导入时间 |

### 5.2 import_history（导入历史表）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| source_path | VARCHAR(1024) | 源路径 |
| target_path | VARCHAR(1024) | 目标路径 |
| total_files | INTEGER | 总文件数 |
| imported_files | INTEGER | 成功数 |
| skipped_files | INTEGER | 跳过数 |
| total_size | INTEGER | 总大小（字节） |
| import_mode | VARCHAR(8) | copy / move |
| started_at | DATETIME | 开始时间 |
| completed_at | DATETIME | 完成时间 |

### 5.3 settings（配置表）
键值对存储应用配置。

---

## 6. 安全设计

- 所有文件操作使用 `relative_to()` 做路径校验，防止路径穿越
- 删除 API 仅限相册目录或显式指定的源目录
- MD5 重建和导入检查任务有 5 分钟 TTL 自动清理
- PyInstaller 打包排除 VCRuntime/Python DLL 避免 UPX 压缩问题

---

## 7. 验收标准

### 7.1 启动
- [ ] 运行 `python src/BlurArc.py` 或打包后的 `BlurArc.exe` 能正常启动
- [ ] PyWebView 窗口显示正确（最大化，暗色主题）
- [ ] Flask API 在 30 秒内就绪，页面正常加载
- [ ] 低端机或首次启动时，等待页面正常显示并自动重连

### 7.2 相册
- [ ] 选择文件夹后，目录树正确显示
- [ ] 照片网格正确显示缩略图
- [ ] 点击照片可查看大图和 EXIF 信息

### 7.3 导入
- [ ] 能正确扫描源文件夹中的媒体文件
- [ ] 两阶段去重工作正常（预筛 + MD5 确认）
- [ ] 复制模式和剪切模式均正常
- [ ] 导入过程中可暂停/继续/取消
- [ ] 进度条实时更新

### 7.4 技术
- [ ] 单元测试全部通过（pytest）
- [ ] 集成测试全部通过
- [ ] 缩略图缓存命中后不再重复生成
- [ ] 视频可正常播放（支持拖动）

---

## 8. 版本历史

| 版本 | 日期 | 主要变化 |
|------|------|---------|
| v0.5 | 当前 | 重命名为 Blur Arc，全面更新项目名称和文档 |
