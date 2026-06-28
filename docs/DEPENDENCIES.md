# 📦 依赖安装指南 v0.6.0

> 同时覆盖 **后端（Python）**、**PC 前端（Node）**、**移动端（Flutter）** 的依赖列表。
>
> **版本**：v0.6.0（2026-06-24）

---

## 快速安装

### 1. 后端

```bash
pip install -r requirements.txt
```

### 2. PC 前端

```bash
cd frontend
npm install
# 第一次启动必须 build
npm run build
```

### 3. 移动端

```bash
cd blurarc_app
flutter pub get
```

### 4. FFmpeg（可选，视频功能需要）

```bash
python scripts/download_ffmpeg.py
```

或手动放 `backend/ffmpeg_binaries/ffmpeg.exe`（项目已集成 8.1.1）。

---

## 后端依赖（Python 3.10+）

来源：`requirements.txt`

| 包名 | 最低版本 | 用途 |
|------|----------|------|
| **Flask** | 2.3.0 | Web 框架（PC + 移动 API 容器） |
| **Flask-CORS** | 4.0.0 | 跨域资源共享 |
| **PyWebView** | 6.1 | 桌面 WebView 窗口 |
| **Pillow** | 10.0.0 | 图像处理 / 缩略图 / EXIF |
| **piexif** | 1.1.3 | EXIF 解析（拍摄日期） |
| **python-dateutil** | 2.8.2 | 日期时间工具 |
| **SQLAlchemy** | 2.0+ | ORM |
| **watchdog** | 4.0+ | 文件监听（可选） |
| **zeroconf** | 0.132+ ⚠️ | mDNS 广播（移动端发现） |
| **PyInstaller** | 6.0+ | 打包（可选） |

### 验证

```bash
python -c "import flask, flask_cors, webview, PIL, piexif, dateutil, sqlalchemy, zeroconf; print('All OK')"
```

### zeroconf 注意事项 ⚠️

**`ServiceInfo` 参数顺序**（0.132+ `addresses` 是 keyword-only）：

```python
# ❌ 错
ServiceInfo(SERVICE_TYPE, name, addresses=[...], port=self.port, ...)

# ✅ 对
ServiceInfo(SERVICE_TYPE, name, port=self.port, addresses=[...], ...)
```

错写 → `TypeError: multiple values for 'port'` → 线程静默失败。详见 [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)「mDNS 参数顺序陷阱」。

---

## PC 前端依赖（Node 18+）

来源：`frontend/package.json`

| 包 | 版本 | 用途 |
|----|------|------|
| **react** | ^19.0.0 | UI 框架 |
| **react-dom** | ^19.0.0 | DOM 渲染 |
| **typescript** | ^5.0.0 | 类型 |
| **vite** | ^7.0.0 | 构建工具 |
| **@vitejs/plugin-react** | ^5.0.0 | React 插件 |
| **tailwindcss** | ^4.0.0 | 原子化 CSS |
| **zustand** | ^4.0.0 | 轻量状态管理 |
| **lucide-react** | ^0.400.0 | 图标库 |

### 开发

```bash
cd frontend
npm run dev     # Vite dev server
npm run build   # 构建到 dist/
npm run preview # 预览 dist
```

---

## 移动端依赖（Flutter 3.44+ / Dart 3.0+）

来源：`blurarc_app/pubspec.yaml`

### 直接依赖

| 包 | 版本 | 用途 |
|----|------|------|
| **dio** | ^5.4.0 | HTTP 客户端（带 sendTimeout 防卡死） |
| **cached_network_image** | ^3.3.0 | 缩略图缓存 |
| **video_player** | ^2.8.0 | 视频播放 |
| **shared_preferences** | ^2.2.0 | 本地 KV 存储（Token / 设备 ID） |
| **provider** | ^6.1.1 | 状态管理 |
| **multicast_dns** | ^0.3.2 | mDNS 发现 PC 端 |
| **path_provider** | ^2.1.0 | 平台路径 |
| **permission_handler** | ^11.0.0 | 权限申请（Android 13+） |
| **image_picker** | ^1.0.0 | 选图 |
| **intl** | ^0.19.0 | 国际化（日期/数字格式化） |
| **flutter_svg** | ^2.0.10 | SVG 渲染（Logo） |
| **device_info_plus** | ^11.5.0 | 设备信息（设备名） |

### 开发依赖

| 包 | 版本 | 用途 |
|----|------|------|
| **flutter_test** | sdk | Widget / 单元测试 |
| **flutter_launcher_icons** | ^0.13.0 | App 图标生成 |
| **flutter_lints** | ^3.0.0 | 静态检查规则 |

### 安装

```bash
cd blurarc_app
flutter pub get
flutter pub deps    # 查看依赖树
```

---

## FFmpeg 集成

| 项 | 值 |
|----|----|
| 版本 | 8.1.1 |
| 位置 | `backend/ffmpeg_binaries/ffmpeg.exe` |
| 平台 | Windows（Linux/macOS 暂未集成） |
| 下载 | `python scripts/download_ffmpeg.py` |
| 大小 | ~80MB |

**用途**：
- 视频缩略图生成
- 元数据提取（时长 / 分辨率 / 编码）
- HTTP Range 切片（拖拽播放）

**不下载也能用**：仅影响视频功能，图片相关不受影响。

---

## 验证

### 一键验证脚本

```bash
# 后端
python -c "
import flask, flask_cors, webview, PIL, piexif, dateutil, sqlalchemy, zeroconf
print('Backend OK')
"

# PC 前端
cd frontend && npx tsc --noEmit && echo "Frontend OK"

# 移动端
cd blurarc_app && flutter doctor -v && flutter analyze
```

---

## 常见问题

### Q1: pip 下载太慢

```bash
# 阿里云
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 清华
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: zeroconf 安装失败

```bash
# zeroconf 需要 cffi，确保系统有 C 编译器
# Windows: 安装 Visual Studio Build Tools
# macOS: xcode-select --install
# Linux: apt install build-essential python3-dev
```

### Q3: Flutter pub get 卡住

```bash
# 配置国内镜像（编辑 ~/.pub-cache/config.json 或 PUB_HOSTED_URL）
export PUB_HOSTED_URL=https://pub.flutter-io.cn
export FLUTTER_STORAGE_BASE_URL=https://storage.flutter-io.cn
flutter pub get
```

### Q4: 版本冲突

```bash
# Python: 用 venv
python -m venv .venv
.\.venv\Scripts\activate

# Node: 用 nvm 切版本
nvm use 18

# Flutter: 切 channel
flutter channel stable
```

### Q5: 缺 FFmpeg

```bash
python scripts/download_ffmpeg.py
# 或手动从 https://www.gyan.dev/ffmpeg/builds/ 下载 essentials 版
# 放到 backend/ffmpeg_binaries/ffmpeg.exe
```

### Q6: PyWebView 启动闪退

- macOS: 安装 `pip install pywebview[qt]` 或 `pyobjc`
- Linux: 安装 `python3-gi`, `gir1.2-gtk-3.0` 等
- Windows: 一般无问题

---

## 升级

### 后端

```bash
pip install --upgrade -r requirements.txt
```

### PC 前端

```bash
cd frontend
npm update
# 或装最新主版本
npx npm-check-updates -u
npm install
```

### 移动端

```bash
cd blurarc_app
flutter pub upgrade
# 或
flutter pub upgrade --major-versions
```

---

## 导出当前环境

```bash
# Python
pip freeze > requirements-frozen.txt

# Node
cd frontend && npm list --depth=0 > npm-frozen.txt

# Flutter
cd blurarc_app && flutter pub deps --json > pubspec-frozen.json
```

---

## 系统要求

| 项 | 最低 | 推荐 |
|----|------|------|
| 操作系统 | Windows 10 / macOS 11 / Ubuntu 20.04 | Windows 11 / macOS 13 / Ubuntu 22.04 |
| Python | 3.10 | 3.11+ |
| Node.js | 18 | 20 LTS |
| Flutter | 3.44 | 3.44+ |
| 内存 | 4GB | 8GB+ |
| 硬盘 | 2GB（不含相册） | SSD |
| 移动端 | Android 8 / iOS 13 | Android 13+ / iOS 16+ |

---

## 进一步阅读

- [QUICK_START.md](QUICK_START.md) — 5 分钟上手
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) — 开发流程
- [blurarc_app/README.md](../blurarc_app/README.md) — 移动端说明

---

**版本**: v0.6.0 · **更新日期**: 2026-06-24
