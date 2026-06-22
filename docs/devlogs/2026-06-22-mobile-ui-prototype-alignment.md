# 2026-06-22 移动端 UI 与原型对齐（10 项修复）

## 背景

平板端 UI 修复后，将手机端也纳入对比。`docs/prototypes/{mobile,tablet}/mobile|tablet-app-v3-{light,dark}.html` 4 个原型与 Flutter 实现逐项对照，发现 10 处差异，全部修复。

## 修复清单

### 1. 暗色 AppBar / BottomNav 背景色 → `bg-page`

**问题：** 暗色模式下 appBarTheme.backgroundColor = `darkBgCard` (`#151d26`)，导致 AppBar、BottomNav、平板工具栏有可见"卡片底"色块。原型暗色模式这些区域都是透明的（页面底 `#0c1117`）。

**修复：** [app_theme.dart:24](file:///f:/AI/Frame_Album/blurarc_app/lib/theme/app_theme.dart#L24) `darkBgCard` → `darkBgPage`（仅 dark theme）。一处改动同时影响 AppBar、BottomNav、平板工具栏（都用 `theme.appBarTheme.backgroundColor`）。

### 2-3. AppBar logo / 文字尺寸

**问题：** logoSize 24px、fontSize 15px / w500。原型 28px / 17px / 600。

**修复：** [blur_arc_logo.dart](file:///f:/AI/Frame_Album/blurarc_app/lib/widgets/blur_arc_logo.dart) 调整默认参数 + 新增 `fontWeight` 字段。

**额外优化：** 之前默认色 `0xFF0891b2`（lightCyan）在暗色下对比度差，改为 `colorScheme.primary`，dark 自动用 `0xFF22D3EE`（更亮的 cyan）。

### 4. 手机相册工具栏下拉箭头

**问题：** 手机工具栏调用 `_OutlineButton` 时未传 `showDropdownArrow`，默认 false。原型是 `📅 + 2026年6月 + ▾`。

**修复：** [album_screen.dart:252](file:///f:/AI/Frame_Album/blurarc_app/lib/screens/album_screen.dart#L252) 显式传 `showDropdownArrow: true`，与平板工具栏一致。

### 5. 手机上传按钮布局 → 上下堆叠

**问题：** `upload_screen._buildBottomActions` 用 Row(全部取消 | 开始上传)。原型 mobile 是 Column(开始上 / 全部取消)；tablet 是 Row(开始上 | 全部取消)。

**修复：** [upload_screen.dart:204-218](file:///f:/AI/Frame_Album/blurarc_app/lib/screens/upload_screen.dart#L204-L218) 抽取 `primaryBtn` / `secondaryBtn` 局部变量，按 `isTablet` 切换布局。**同时调整了按钮顺序**（之前次按钮在前，与原型相反）。

### 6. Settings 主题选项顺序

**问题：** 跟随系统 / 浅色 / 深色。原型 跟随系统 / 深色 / 浅色。

**修复：** [settings_screen.dart:243-247](file:///f:/AI/Frame_Album/blurarc_app/lib/screens/settings_screen.dart#L243-L247) 数组顺序调整。

### 7-8. Section header 平台差异化

**问题：** 之前 mobile/tablet 共用 `padding 16×14×8 + font 13px`。原型 mobile `14×12×8 + 13px`，tablet `16×16×8 + 14px`。

**修复：** [album_screen.dart:496-504](file:///f:/AI/Frame_Album/blurarc_app/lib/screens/album_screen.dart#L496-L504) `_SectionBlock` 新增 `isTablet` 参数，按平台决定 padding/fontSize。`hPad` 仍参与 tablet 水平偏移，mobile 直接用 12px。

### 9. 手机 Settings 区块标题

**问题：** 原型 mobile 有 `settings-section-title`（"设备信息" / "显示" / "关于"，12px 大写 + letter-spacing 0.5 + 浅色），当前所有平台都没显示。

**修复：** [settings_screen.dart](file:///f:/AI/Frame_Album/blurarc_app/lib/screens/settings_screen.dart)
- 新增 `_SettingsSectionTitle` 组件（uppercase + 12px + letter-spacing 0.5 + onSurface alpha 120）
- 用 `if (!isTablet)` 条件包裹，**仅 mobile 显示**（tablet 原型本身无 section title）

### 10. 手机 Folder 返回按钮 → `‹ 返回相册`

**问题：** Folder 屏 mobile/tablet 都用 AppBar 显示路径标题。原型 mobile 无 AppBar，顶部只有 `‹ 返回相册` 简单文本。

**修复：** [folder_screen.dart:70-103](file:///f:/AI/Frame_Album/blurarc_app/lib/screens/folder_screen.dart#L70-L103)
- mobile：`appBar: null`，body 顶部加 `‹ 返回相册` 文本按钮（`InkWell` + `Navigator.pop`）
- tablet：保留 AppBar + 路径标题

## 验证

```
$ flutter analyze
Analyzing blurarc_app...
No issues found! (ran in 2.0s)
```

## 涉及文件

- `blurarc_app/lib/theme/app_theme.dart`
- `blurarc_app/lib/widgets/blur_arc_logo.dart`
- `blurarc_app/lib/screens/album_screen.dart`
- `blurarc_app/lib/screens/upload_screen.dart`
- `blurarc_app/lib/screens/settings_screen.dart`
- `blurarc_app/lib/screens/folder_screen.dart`
- `blurarc_app/lib/screens/home_page.dart`（间接：移除 logoSize 显式参数，使用新默认值）

## 设计原则

- **平台差异用 `isTablet = MediaQuery.size.width > 600` 判别**，与 `album_screen._isTablet` 等保持一致
- **新组件命名 `_Private`**（下划线前缀），符合 Dart 文件私有组件约定
- **每个差异独立 commit message**，便于回溯
