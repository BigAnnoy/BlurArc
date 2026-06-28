# 🚀 Blur Arc 入门指南 v0.6.0

> 从零开始使用 Blur Arc：**PC 端 + 移动端**。
>
> **版本**：v0.6.0（2026-06-24）

---

## 1️⃣ Blur Arc 是什么？

Blur Arc 是一个 **本地优先** 的照片管理器，由两部分组成：

| 端 | 形态 | 作用 |
|----|------|------|
| **PC 端** | PyWebView + React 桌面应用 | 主战场：浏览、导入、归档、管理相册 |
| **移动端** | Flutter 移动 App | 浏览相册、推送照片到 PC |

### 核心特性

- 📁 **EXIF 自动归档**：按拍摄日期整理到 `YYYY/YYYY-MM/`
- 🔍 **两阶段去重**：按大小预筛 + MD5 校验
- 🎬 **视频原生支持**：FFmpeg 8.1.1 集成
- 📱 **移动互联**：mDNS 自动发现 + 6 位配对码 + Token 鉴权
- 🌓 **暗/亮主题**：PC 端 + 移动端统一
- 📱 **跨端适配**：手机竖屏、平板横屏、桌面响应式

### 适用场景

- 📷 **手机照片集中管理**：每月手机照片太多？推到 PC 自动归档
- 🗂️ **多设备相册统一**：手机/相机/截图统一在 PC 端管理
- 🚫 **避免重复导入**：多次导入同一文件夹不会产生重复
- 🔒 **完全本地**：所有照片、数据库都在你自己的机器上

---

## 2️⃣ 安装

### PC 端

**系统要求**：Windows 10+ / macOS 11+ / Ubuntu 20.04+

**依赖**：
- Python 3.10+
- Node.js 18+（PC 前端构建用，已 build 可跳过）
- FFmpeg（可选，视频功能需要；项目已集成）

**步骤**：

```bash
# 克隆
git clone https://github.com/BigAnnoy/BlurArc.git
cd BlurArc

# Python 依赖
pip install -r requirements.txt

# PC 前端（第一次必须 build，否则 PyWebView 加载不到 dist/）
cd frontend
npm install
npm run build
cd ..

# 启动
python src/BlurArc.py
```

### 移动端

**要求**：
- Flutter SDK 3.44+（[官方安装](https://docs.flutter.dev/get-started/install)）
- Android Studio / Xcode（Android / iOS 编译）
- 真机（推荐）或模拟器

**步骤**：

```bash
cd blurarc_app
flutter pub get
flutter run            # 启动到默认设备
```

---

## 3️⃣ 第一次使用 PC 端

### 3.1 选择相册根目录

启动后会弹 **欢迎页**，点「**选择相册文件夹**」。

> 建议选一个空目录作为相册根目录，Blur Arc 会把照片按 `YYYY/YYYY-MM/` 自动归档到此目录。

### 3.2 导入第一批照片

点工具栏「**导入**」：

1. 选一个有照片的源文件夹
2. 工具会先做 **预检**：新增 / 源内重复 / 目标重复
3. 确认后点「**开始导入**」
4. 进度条实时刷新，可暂停/继续/取消

### 3.3 浏览

- 左侧：**目录树**（年 → 月）
- 右侧：**照片网格**（缩略图）
- 点照片：放大预览
- 顶部「**选择**」：进入批量模式，可多选删除

### 3.4 修改设置

点「**设置**」可调整：
- 主题（暗/亮/跟随系统）
- 相册路径
- 缩略图质量
- 移动接入服务开关

---

## 4️⃣ 第一次连接移动端

### 4.1 前提

- ✅ PC 端已启动
- ✅ 移动接入服务已开启（PC 端默认开）
- ✅ 手机和 PC 在 **同一 WiFi**

### 4.2 移动端发现 PC

打开移动端 App：

- **自动**：mDNS 发现局域网内 PC（`_blurarc._tcp.local.`）
- **手动**：在连接页点「**手动输入 IP**」，填 `PC_IP:8900`

> **模拟器用户**：Android 模拟器不支持 mDNS，必须手动输 `10.0.2.2:8900`

### 4.3 配对

1. 移动端选 PC → 跳「**输入配对码**」页
2. PC 端弹一个 **6 位配对码** 窗口
3. 在移动端输入配对码
4. PC 端点「**确认**」
5. 配对成功，移动端获得 Token，自动跳首页

**配对信息**：
- 存于 `shared_preferences`（移动端）
- 存于 `mobile_devices` 表（PC 端）
- 持久化：下次启动移动端自动连接

### 4.4 浏览 + 上传

**浏览**：
- 首页按月份分组的照片墙
- 点开看大图、滑动切换
- 「**下载原图**」按钮可保存到手机

**上传**：
1. 底部「**上传**」Tab
2. 点「**+**」选图
3. 选完点「**上传**」
4. PC 端会自动弹 **ImportDialog**
5. 确认即可一键导入

---

## 5️⃣ 进阶玩法

### 5.1 性能优化

如果你的相册有几万张照片：

```bash
# 第一次导入会算 MD5，慢一点
# 之后的导入会命中 DB 缓存，极快
```

清理缩略图缓存：
```bash
# 缩略图缓存位置
~/.photomanager/thumbnails/
# 直接删即可，工具会按需重新生成
```

### 5.2 多相册

目前是单相册（用户自选根目录）。未来支持多相册切换。

### 5.3 自定义归档规则

未来计划：让用户自定义 EXIF 字段 → 路径映射。当前固定 `YYYY/YYYY-MM/`。

### 5.4 备份

相册文件夹直接 rsync / 备份到云盘即可。数据库是 SQLite，单文件。

---

## 6️⃣ 常见问题

### ❓ PC 端启动闪退

- 检查 Python 版本 `python --version`（要 3.10+）
- 重新装依赖 `pip install -r requirements.txt --force-reinstall`
- 看 `BlurArc.log` 日志

### ❓ 移动端找不到 PC

- 同 WiFi？
- PC 防火墙 8900 端口放行？
  - Windows：`netsh advfirewall firewall add rule name="BlurArc Mobile" dir=in action=allow protocol=TCP localport=8900`
  - macOS：系统设置 → 网络 → 防火墙
- 模拟器需手动输 IP

### ❓ 视频播放不了

- 看 FFmpeg 是否下载：`python scripts/download_ffmpeg.py`
- 看 `backend/ffmpeg_binaries/ffmpeg.exe` 是否存在

### ❓ 移动端首屏卡死

已修复（v0.5.3），确保 `api_client.dart` 配 `Dio(sendTimeout: 30s)`。

### ❓ PC 前端改了不生效

```bash
# PyWebView 加载的是 dist/，改了代码必须 build
cd frontend && npm run build
```

### ❓ 移动端热更新没反应

- 模拟器按 `r`（hot reload）/ `R`（hot restart）
- 真机重装 APK

---

## 7️⃣ 下一步

- 📚 阅读 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) 速查
- 🗺️ 阅读 [CODE_MAP.md](CODE_MAP.md) 了解代码组织
- 🔌 阅读 [API_REFERENCE.md](API_REFERENCE.md) 了解 API
- 🛠️ 阅读 [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) 参与开发

---

**状态**：✅ PC 端 + 移动端双端可用  
**版本**：v0.6.0  
**更新日期**：2026-06-24
