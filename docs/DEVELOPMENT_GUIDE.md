# 开发指南

> 更新日期：2026-06-16
> 版本：v0.5.0

## 环境准备

### 系统要求

- Python 3.8+
- Windows / macOS / Linux

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/BigAnnoy/BlurArc.git
cd BlurArc

# 安装依赖
pip install -r requirements.txt
```

### 依赖列表

**后端依赖**
| 包名 | 版本 | 用途 |
|------|------|------|
| Flask | 2.3+ | Web 框架 |
| Flask-CORS | - | 跨域支持 |
| PyWebView | 6.1+ | 桌面窗口 |
| SQLAlchemy | 2.0+ | ORM |
| Pillow | 10+ | 图像处理 |
| pillow-heif | - | HEIC 支持 |

**前端依赖**
| 包名 | 版本 | 用途 |
|------|------|------|
| React | 19.2+ | UI 框架 |
| TypeScript | 6.0+ | 类型检查 |
| Vite | 8.0+ | 构建工具 |
| Tailwind CSS | 4.3+ | 样式框架 |

---

## 项目结构

```
BlurArc/
├── src/
│   └── BlurArc.py          # 主入口
├── backend/
│   ├── __init__.py
│   ├── api_server.py          # Flask REST API
│   ├── import_manager.py      # 导入管理器
│   ├── thumbnail_manager.py   # 缩略图管理
│   ├── video_processor.py     # 视频处理
│   ├── database.py            # 数据模型
│   ├── config_manager.py      # 配置管理
│   ├── constants.py           # 常量定义
│   ├── utils.py               # 工具函数
│   └── ffmpeg_binaries/       # FFmpeg 二进制
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # 主应用组件
│   │   ├── components/        # UI 组件
│   │   ├── services/api.ts    # API 服务
│   │   ├── hooks/             # 自定义 Hooks
│   │   └── types/             # TypeScript 类型
│   ├── package.json
│   └── vite.config.ts
├── scripts/                   # 工具脚本
├── test/                      # 测试用例
│   ├── unit/                  # 单元测试
│   └── api/                   # API 测试
└── docs/                      # 文档
```

---

## 开发命令

### 启动应用

```bash
# 开发模式启动（后端 + 前端）
python src/BlurArc.py

# 或直接运行后端（用于调试）
python -m backend.api_server
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 开发模式（热更新）
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview

# 代码检查
npm run lint
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest test/unit/ -v

# 运行单个测试文件
pytest test/unit/test_import_manager_pytest.py -v

# 带覆盖率
pytest --cov=backend test/unit/
```

### 代码检查

```bash
# 类型检查
mypy backend/

# 代码格式化
black backend/
black frontend/modules/
```

---

## 核心模块说明

### 1. api_server.py

Flask 应用入口，定义所有 API 端点。

**关键函数**
- `get_album_stats()` - 统计信息
- `get_photos()` - 照片列表
- `start_import()` - 启动导入
- `delete_files()` - 批量删除

### 2. import_manager.py

导入逻辑核心，处理文件导入和去重。

**关键类和方法**
```python
class ImportManager:
    def start_import_async(...)  # 异步启动导入
    def _do_import(...)          # 导入主流程
    def _import_file(...)        # 导入单个文件
    def _compute_md5(...)        # 计算 MD5
    def _load_target_records(...) # 加载已有记录
```

**性能优化**
- MD5 缓存复用
- 并行源去重
- 两阶段预筛

### 3. video_processor.py

FFmpeg 封装，处理视频相关操作。

**关键方法**
```python
class VideoProcessor:
    @staticmethod
    def is_ffmpeg_available() -> bool
    
    @staticmethod
    def generate_thumbnail(video_path, output_path, time_seconds) -> bool
    
    @staticmethod
    def extract_metadata(video_path) -> Optional[Dict]
    
    @staticmethod
    def get_video_duration(video_path) -> Optional[float]
```

### 4. thumbnail_manager.py

缩略图生成和缓存管理。

**关键方法**
```python
class ThumbnailManager:
    def get_thumbnail(photo_path, size) -> Optional[str]
    def generate_thumbnail(photo_path, output_path, size) -> bool
    def clear_cache(older_than_days) -> int
```

### 5. utils.py

工具函数集合。

```python
def compute_md5(path, chunk_size=1024*1024) -> Optional[str]
def get_file_fingerprint(path) -> Optional[Tuple[int, float]]
```

---

## 添加新功能

### 添加新的 API 端点

1. 在 `api_server.py` 中定义路由：

```python
@app.route('/api/new-endpoint', methods=['GET'])
def new_endpoint():
    # 处理逻辑
    return jsonify({"result": "ok"})
```

2. 在 `frontend/modules/api/` 中添加调用方法：

```javascript
async function newEndpoint() {
    const response = await fetch('/api/new-endpoint');
    return response.json();
}
```

### 添加新的媒体格式支持

1. 在 `constants.py` 中添加格式：

```python
MEDIA_FORMATS.add('.newformat')
VIDEO_FORMATS.add('.newformat')  # 如果是视频
```

2. 如果需要特殊处理，在相应模块添加逻辑。

---

## 调试技巧

### 后端调试

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 在代码中
logger.debug(f"调试信息: {variable}")
```

### 查看数据库

```bash
# 使用 sqlite3 命令行
sqlite3 .config/photo_manager.db

# 常用查询
.tables
.schema photos
SELECT * FROM photos LIMIT 10;
```

### 查看 API 响应

```bash
# 健康检查
curl http://localhost:5000/api/health

# 统计信息
curl http://localhost:5000/api/album/stats
```

---

## 打包发布

### 使用 PyInstaller

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller BlurArc.spec

# 输出
dist/BlurArc.exe
```

### 打包配置 (BlurArc.spec)

关键配置项：
- `datas`: 包含前端文件和 FFmpeg
- `hiddenimports`: 隐式导入的模块
- `excludes`: 排除的模块

---

## 性能优化指南

### 已实现的优化

| 优化项 | 实现位置 | 效果 |
|--------|----------|------|
| MD5 缓存 | `import_manager.py` | 减少 50-70% 计算 |
| 并行去重 | `import_manager.py` | 2-4x 提升 |
| 两阶段预筛 | `import_manager.py` | 5-10x 提升 |

### 可继续优化

| 方案 | 效果 | 复杂度 |
|------|------|--------|
| 增量 MD5 | 大文件 3-5x | 中 |
| xxHash | 5-10x | 低 |
| 异步视频元数据 | 不阻塞导入 | 中 |

---

## 常见问题

### Q: FFmpeg 不可用？

A: 运行 `python scripts/download_ffmpeg.py` 或手动下载到 `backend/ffmpeg_binaries/`。

### Q: 导入速度慢？

A: 
1. 检查是否启用了 `skip_source_duplicates` 和 `skip_target_duplicates`
2. 确保两阶段预筛生效（查看日志中的"预筛完成"）
3. 考虑减少并发线程数（修改 `max_workers`）

### Q: 缩略图不显示？

A:
1. 检查 `.thumbnails/` 目录权限
2. 检查 pillow-heif 是否安装（HEIC 支持）
3. 查看日志中的错误信息

---

## 贡献指南

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -m 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交 Pull Request

### 代码规范

- 使用 4 空格缩进
- 函数添加文档字符串
- 新功能需要测试用例
- 遵循 PEP 8 规范
