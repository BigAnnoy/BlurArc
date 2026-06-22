# 2026-06-22 平板模拟器搭建 + 三项 UI 细节修复

## 背景

平板模拟器搭建需求：
- dev-start.bat 缺少"部署到平板模拟器"和"启动 PC app"选项
- AVD `BlurArc_Tablet` 未创建
- 平板模拟器默认 density 与真机 Pixel Tablet（213dpi）不一致，导致缩放与 prototype 不匹配
- 平板上 ConnectScreen 在小屏横屏状态下 `bottom overflowed by 223 pixels`

UI 细节差异（用户截图反馈）：
- 平板 sidebar 顶部"相册"二字在 Column 中默认 `crossAxisAlignment: center`，导致居中而非左对齐
- sidebar 月份列表项缺小图标（prototype 用 18px emoji）
- 工具栏"跳转月份"按钮用的是 Material `Icons.calendar_today`（带方框的图标），与 prototype 的 `📅` emoji 视觉差异大

## 主要改动

### 1. dev-start.bat 新增菜单项 [7][8]

[scripts/dev-start.bat](../../scripts/dev-start.bat) 顶部配置：
- 新增 `AVD_TABLET_NAME=BlurArc_Tablet`

菜单项：
- `[7] Deploy to tablet emulator`：复用 `:build_apk` 逻辑，启动 BlurArc_Tablet AVD（带 `-skin 1280x800`），等待 boot 完成后 install + launch
- `[8] Run PC app (frontend build + BlurArc.py)`：先 `cd frontend && npm run build`，然后 `start python src/BlurArc.py`（不构建 exe，开发用）

### 2. 创建 BlurArc_Tablet AVD

通过 `avdmanager create avd` 创建：
- 设备模板：`pixel_tablet`（Android Studio AVD Manager 的 Pixel Tablet 模板）
- System Image：`system-images;android-34;google_apis_playstore;x86_64`
- 路径：`C:\Users\BIGANNOY\.android\avd\BlurArc_Tablet.avd`

启动参数：
```
emulator.exe -avd BlurArc_Tablet -skin 1280x800
```

`-density` 启动参数在新版 emulator 中不支持，改用 AVD config.ini 持久化。

### 3. AVD density 调整为 213

[c:\Users\BIGANNOY\.android\avd\BlurArc_Tablet.avd\config.ini](../../.android/avd/BlurArc_Tablet.avd/config.ini)：
```diff
-hw.lcd.density=320
+hw.lcd.density=213
```

最终模拟器参数（与真机 Pixel Tablet 物理一致）：
- Physical size: 1280×800
- Physical density: 213
- 逻辑分辨率: 960×600dp
- 1dp 物理尺寸: 1.33px（= 1/160 inch，Android dp 标准）

这让 1dp 物理尺寸与真机完全一致，UI 元素在 AVD 上不再显得"过大"。

### 4. ConnectScreen 修复平板 overflow

[connect_screen.dart](../../blurarc_app/lib/screens/connect_screen.dart) 重构 `_buildDiscoveryBody()`：

**之前**：单一 `Column + Expanded` 结构，当无设备列表时显示 `_buildManualEntry()`，高度超 400dp 横屏会 overflow。

**之后**：按状态拆分：
- 有设备列表：`Column + Expanded(ListView)` — 列表可滚动
- 无设备列表（手动输入/扫描中）：`SingleChildScrollView` 包整个 body — 防止 overflow
- `_pcOffline` 状态：Center 内也用 `SingleChildScrollView` 兜底

这样在 400dp 高度的平板横屏下，无论哪种状态都不会 overflow。

### 5. Sidebar "相册" header 左对齐

[tablet_sidebar.dart](../../blurarc_app/lib/widgets/tablet_sidebar.dart)：
- 问题：Text 在 Column 中默认按 `crossAxisAlignment: center` 居中显示
- 修复：`Align(alignment: Alignment.centerLeft, child: Text(...))`

### 6. Sidebar item 加 calendar 图标

[tablet_sidebar.dart](../../blurarc_app/lib/widgets/tablet_sidebar.dart) `_SidebarItem`：
- 在 text 前加 16px `Icons.calendar_today_outlined` + 10dp 间距
- 颜色 `textColor.withAlpha(160)` 与文字同色系
- 位置：active 时 3px 竖条后插入 icon，non-active 时 13dp 占位 + icon

### 7. 跳转月份按钮 icon 改 emoji 📅

[album_screen.dart](../../blurarc_app/lib/screens/album_screen.dart)：
- 工具栏"跳转月份"按钮：`Icons.calendar_today` → emoji `📅`
- date panel 顶部"跳转月份 ▼"按钮：同上
- 顺带把 `_OutlineButton` 重构为支持 `icon` 或 `emoji` 二选一参数（`assert(icon != null || emoji != null)`），更灵活

## 验证

- `flutter analyze` → `No issues found! (ran in 2.0s)`
- AVD 启动参数验证（adb shell wm）：
  ```
  Physical size: 1280x800
  Physical density: 213
  sys.boot_completed: 1
  ```
- APK 安装：`adb install -r .../app-debug.apk` → `Success`
- 用户实测："现在正常了"（缩放问题已解决）
- 3 项 UI 细节修复后用户确认

## 后续

- 手机端 UI 排查（之前只在平板模拟器测过）
- 继续对比 prototype 找剩余差异
- TRAE-code-review 代码审查
