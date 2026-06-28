# Blur Arc — 移动端 App

> 局域网无线浏览相册、推送照片到 PC 端，与 [Blur Arc](../README.md) 配套使用。
>
> **版本：** 1.0.0+1（App 内部版本）· **配套 PC 端：** v0.6.0+

---

## 简介

`blurarc_app` 是 Blur Arc 的 Flutter 移动端伴侣 App，运行在 Android / iOS 手机和平板上。

通过局域网 mDNS 自动发现 PC 端、配对成功后即可：
- **浏览相册**：按月份分组的照片墙，流畅滚动，大图预览
- **查看原图**：缩略图 → 中等预览 → 一键下载原图到本地
- **上传照片**：手机相册批量选图，推送到 PC 端自动归档
- **跨设备**：手机竖屏、平板横屏自动适配，统一暗/亮主题

**App 内部版本 `1.0`** — 与 PC 端 `v0.6.0` 解耦，移动端 API 通过 `/api/mobile/upload/done` 通知 PC 端有新的 Flutter 上传需要处理。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 框架 | Flutter 3.44+ (Dart SDK `>=3.0.0 <4.0.0`) |
| HTTP | Dio 5.4+（带 sendTimeout，修复首屏卡死） |
| 局域网发现 | multicast_dns 0.3+ |
| 状态管理 | Provider 6.1+ |
| 图片缓存 | cached_network_image 3.3+ |
| 视频播放 | video_player 2.8+ |
| 本地存储 | shared_preferences 2.2+ |
| 选图 | image_picker 1.0+ |
| 权限 | permission_handler 11.0+ |
| SVG 渲染 | flutter_svg 2.0+ |
| 设备信息 | device_info_plus 11.5+ |
| 文件路径 | path_provider 2.1+ |
| 国际化 | intl 0.19+ |
| 应用图标 | flutter_launcher_icons 0.13+ |

完整依赖见 [pubspec.yaml](./pubspec.yaml)。

---

## 项目结构

```
blurarc_app/
├── lib/
│   ├── main.dart                       # 入口 + Provider 链
│   ├── screens/                        # 页面
│   │   ├── connect_screen.dart         # mDNS 发现 + 发起配对
│   │   ├── pairing_code_screen.dart    # 输入配对码
│   │   ├── home_page.dart              # 主壳（侧边栏 / 底部 Tab）
│   │   ├── album_screen.dart           # 月份分组照片墙
│   │   ├── folder_screen.dart          # 文件夹浏览
│   │   ├── month_photo_screen.dart     # 单月照片平铺
│   │   ├── photo_grid_screen.dart      # 通用照片网格
│   │   ├── photo_preview_screen.dart   # 大图查看 + 下载原图
│   │   ├── upload_screen.dart          # 选图 + 上传
│   │   └── settings_screen.dart        # 主题 / 设备信息 / 断开
│   ├── services/                       # 服务层
│   │   ├── api_client.dart             # PC 端 API 调用（含 Token 鉴权）
│   │   ├── mdns_discovery.dart         # mDNS 客户端
│   │   ├── device_info_service.dart    # 跨平台设备名
│   │   └── theme_provider.dart         # 主题状态
│   ├── models/                         # 数据模型
│   │   ├── photo.dart
│   │   ├── photo_section.dart
│   │   ├── photo_section_with_photos.dart
│   │   ├── folder_entry.dart
│   │   ├── album_tree.dart
│   │   └── upload_item.dart
│   ├── widgets/                        # 通用组件
│   │   ├── blur_arc_logo.dart          # Logo SVG（双主题）
│   │   ├── bottom_tab_bar.dart         # 底部 Tab（手机）
│   │   ├── tablet_sidebar.dart         # 侧边栏（平板）
│   │   ├── month_calendar_sheet.dart   # 月份跳转日历
│   │   ├── photo_card.dart             # 照片卡片
│   │   ├── responsive_layout.dart      # 响应式布局工具
│   │   ├── step_indicator.dart         # 步骤指示器
│   │   ├── tree_view.dart              # 树视图
│   │   └── upload_progress.dart        # 上传进度条
│   └── theme/
│       ├── app_theme.dart              # 主题样式
│       └── colors.dart                 # 调色板
├── assets/
│   ├── logo/                           # Logo SVG / PNG（双主题）
│   │   ├── blur_arc_logo_dark.svg
│   │   ├── blur_arc_logo_light.svg
│   │   ├── icon_512.png
│   │   └── icon_512_light.png
│   └── images/                         # 顶部栏背景图
│       ├── title_bar_dark.png
│       └── title_bar_light.png
├── android/  ios/  macos/  windows/  linux/  web/   # 平台目录
├── test/                               # 单元 / Widget 测试
└── pubspec.yaml
```

模块地图与改某功能时去哪改，见仓库根 [docs/CODE_MAP.md](../docs/CODE_MAP.md) 「Flutter App」一节。

---

## 启动流程

### 1. PC 端准备

启动 [Blur Arc PC 端](../README.md)，移动接入服务会自动开启并通过 mDNS 广播 `_blurarc._tcp.local.`。

### 2. 手机端发现 + 配对

```
ConnectScreen
  ↓ mDNS 发现 → DiscoveredService 列表
  ↓ 点击 PC → ApiClient.pairingRequest(deviceName)
        POST /api/mobile/pairing/request
  ↓ 跳 PairingCodeScreen
  ↓ 输入 PC 端弹窗显示的 6 位配对码
  ↓ ApiClient.pairingSubmitCode(code)
        POST /api/mobile/pairing/submit-code
  ↓ PC 端确认 → 获得 Token
  ↓ 跳 HomePage
```

### 3. 配对状态持久化

- Token 与设备 ID 存于 `shared_preferences`
- 启动时自动读取：已有 Token → 直接进 HomePage；无 → ConnectScreen
- 在 SettingsScreen 可一键「断开并清除配对」

---

## 开发

### 环境

```bash
# Flutter SDK（项目根用户的 .trae 配置：E:\Applications\flutter）
flutter --version    # 应 >= 3.44
```

### 安装依赖

```bash
cd blurarc_app
flutter pub get
```

### 代码分析

```bash
flutter analyze
```

### 跑测试

```bash
flutter test
```

### 运行（真机 / 模拟器）

```bash
# 真机
flutter run -d <device-id>

# 所有设备
flutter devices
```

**热更新**：模拟器按 `r`（hot reload）/ `R`（hot restart）；真机重装。

### 真机 vs 模拟器

| 场景 | 真机 | 模拟器 |
|------|------|--------|
| mDNS 自动发现 | ✅ 可用 | ❌ Android 模拟器不支持组播（NAT 隔离） |
| 手动配对 | ✅ | ✅ 需手动输入 PC IP，PC 端输入 `10.0.2.2:8900` |

### 构建

```bash
# Android APK
flutter build apk
# → build/app/outputs/flutter-apk/app-release.apk

# iOS
flutter build ios

# Web
flutter build web
```

### dev-start 快捷菜单

项目根 `scripts/dev-start.ps1` 提供 `[9]` / `[10]` 快捷选项：
- `[9]` = `flutter run`（默认设备）
- `[10]` = 启动后自动 hot reload

---

## 已知约束

- **mDNS 在 Android 模拟器无效**：NAT 隔离，组播不通，必须用真机或手动输入 IP
- **ServiceInfo 参数顺序**（PC 端）见 [../CLAUDE.md](../CLAUDE.md) 中的 mDNS 注意事项
- **首屏秒加载**：`api_client.dart` 配置 `Dio(sendTimeout: 30s)` 防止卡死
- **App 版本与 PC 端版本解耦**：App 内部版本 `1.0`，与 PC 端 `v0.6.0` 不绑定

---

## 原型 / 设计

设计稿在仓库根 `docs/prototypes/mobile/` 与 `docs/prototypes/tablet/`：
- `mobile-app-v3-dark.html` / `mobile-app-v3-light.html` — v3 主框架
- `mobile-app-connect-dark.html` / `mobile-app-connect-light.html` — 连接页
- `tablet-app-v3-dark.html` / `tablet-app-v3-light.html` — 平板 v3

修改 UI **必须先在 `docs/prototypes/` 改 HTML 原型**，确认后再改代码。约定见 [docs/prototypes/README.md](../docs/prototypes/README.md)。

---

## 相关文档

- 项目根 [README.md](../README.md)
- [docs/CODE_MAP.md](../docs/CODE_MAP.md) — 移动端模块地图
- [docs/API_REFERENCE.md](../docs/API_REFERENCE.md) — PC 端 + 移动端 API
- [docs/DEVELOPMENT_GUIDE.md](../docs/DEVELOPMENT_GUIDE.md) — 后端 + Flutter 端开发
- [docs/superpowers/specs/2026-06-19-mobile-ui-redesign.md](../docs/superpowers/specs/2026-06-19-mobile-ui-redesign.md) — 移动端 UI 重设计方案
- devlog：[docs/devlogs/2026-06-18-mobile-access.md](../docs/devlogs/2026-06-18-mobile-access.md) 起，按日期倒序浏览

---

**状态：** ✅ 与 PC 端 v0.6.0 配套可用
