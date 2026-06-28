# 📸 Blur Arc v0.6.0 — 快速测试指南

> 同时覆盖 PC 端 + 移动端的快速上手。
>
> **版本**：v0.6.0（2026-06-24）

---

## 🚀 5 分钟跑通 PC 端

### 步骤 1：安装依赖

```bash
git clone https://github.com/BigAnnoy/BlurArc.git
cd BlurArc
pip install -r requirements.txt
```

### 步骤 2：启动 PC 端

```bash
python src/BlurArc.py
```

首次启动会弹出 **欢迎页**，点「**选择相册文件夹**」选一个空目录作为相册根目录。

### 步骤 3：导入照片

点顶部「**导入**」按钮，选一个有照片的源文件夹：

- 工具会自动按 EXIF 拍摄日期归档到 `YYYY/YYYY-MM/`
- 预检会显示：新增 / 源内重复 / 目标重复 三类
- 进度条实时刷新，可随时暂停/继续/取消

### 步骤 4：浏览

- 左侧：年/月目录树
- 右侧：照片网格（缩略图）
- 顶部「**选择**」进入批量模式，可多选删除

---

## 📱 5 分钟跑通移动端

### 前提

- PC 端已启动（移动接入服务会自动开启）
- 手机和 PC 在 **同一局域网**（同一 WiFi）

### 步骤 1：装依赖

```bash
cd blurarc_app
flutter pub get
```

### 步骤 2：连真机 / 模拟器

```bash
flutter devices    # 查看可用设备
flutter run        # 启动到默认设备
```

### 步骤 3：配对

1. 移动端打开 → 自动 mDNS 发现 PC（确保同 WiFi）
2. 列表里点 PC → 跳「**输入配对码**」页
3. PC 端会弹一个 **6 位配对码** 窗口，输入
4. PC 端点「**确认**」→ 移动端获得 Token → 自动跳首页

> **模拟器限制**：Android 模拟器不支持 mDNS（NAT 隔离），需手动输入 PC IP。模拟器内 `10.0.2.2` 等于宿主机的 `localhost`。
> 模拟器启动方式：在 PC 端点「开始配对」弹配对码，手机端「手动输入 IP」填 `10.0.2.2:8900`。

### 步骤 4：浏览 + 上传

- 浏览：首页按月份分组的照片墙，点开查看大图
- 上传：底部「**上传**」Tab → 选图 → 推送
- 上传完成后 PC 端会自动弹 **ImportDialog**，点确认即可一键导入

---

## 🧪 验收清单

跑通以下 5 项就算熟悉了：

- [ ] PC 端导入 1 个有 10 张照片的文件夹，观察归档结果
- [ ] PC 端同一文件夹再导一次，应该全部判为「目标重复」
- [ ] PC 端点「**设置**」→ 修改主题 / 修改相册路径
- [ ] 移动端 mDNS 发现 PC + 完成配对
- [ ] 移动端选 2 张图上传，PC 端弹 ImportDialog

---

## 🔧 关键命令

```bash
# PC 端
python src/BlurArc.py                  # 启动
cd frontend && npm run dev             # PC 前端开发模式（热更新）
cd frontend && npm run build           # 构建前端产物
pytest                                 # 后端测试
pytest test/unit/ -v                   # 仅单元测试

# 移动端
cd blurarc_app
flutter pub get                        # 装依赖
flutter run                            # 跑（默认设备）
flutter test                           # 移动端测试
flutter analyze                        # 静态检查
flutter build apk                      # 打包 Android APK

# dev-start 快捷菜单（推荐）
.\scripts\dev-start.ps1
# [5] = PC 端（前端 build + BlurArc.py）
# [9] = 启动 Flutter
# [10] = 启动 Flutter + hot reload
```

---

## 🗂️ 项目结构

```
BlurArc/
├── src/BlurArc.py                 # PC 端主入口
├── backend/                       # Python 后端
│   ├── api_server.py              # PC 端 API（35+ 端点）
│   ├── mobile_access_server.py    # 移动端独立 API（20+ 端点）
│   ├── zeroconf_publisher.py      # mDNS 广播
│   ├── import_manager.py          # 导入 + 两阶段去重
│   ├── thumbnail_manager.py       # 缩略图
│   ├── video_processor.py         # FFmpeg
│   ├── database.py                # ORM
│   └── ffmpeg_binaries/           # FFmpeg 8.1.1
├── frontend/                      # PC 端 React + TS + Vite
├── blurarc_app/                   # 移动端 Flutter
│   ├── lib/screens/               # 10 个页面
│   ├── lib/services/              # API Client / mDNS / 主题
│   └── pubspec.yaml
├── docs/                          # 文档 + 原型 + devlog
├── scripts/                       # 启动 / 构建脚本
├── test/                          # pytest
└── BlurArc.spec                   # PyInstaller 打包
```

---

## ❓ 常见问题

**Q：移动端找不到 PC？**
- 确认同 WiFi
- 确认 PC 防火墙允许 8900 端口（移动接入服务端口）
- 模拟器不支持 mDNS，需手动输 IP

**Q：PC 端导入卡住？**
- 看进度条：是否在算 MD5
- 大量文件可暂停，调整源/目标后重试

**Q：移动端上传后 PC 端没弹？**
- 看 PC 端 ImportDialog 是否被遮挡
- 检查 `/api/mobile/pending-flutter-uploads` 是否有记录

**Q：FFmpeg 找不到？**
- 运行 `python scripts/download_ffmpeg.py`
- 不下载时图片功能正常

---

## 📚 进一步阅读

- [README.md](../README.md) — 项目总览
- [blurarc_app/README.md](../blurarc_app/README.md) — 移动端完整说明
- [docs/CODE_MAP.md](CODE_MAP.md) — 模块地图
- [docs/API_REFERENCE.md](API_REFERENCE.md) — 全部 API
- [docs/DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) — 开发指南

---

**祝你玩得开心！** 🎉
