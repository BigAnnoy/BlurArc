# UI 细节对齐原型图 — 8 项修复

**日期：** 2026-06-22
**主题：** 移动端 UI 与原型图细节对齐（边框、图标、间距）

## 背景

`docs/prototypes/mobile/` 与 `docs/prototypes/tablet/` 下的原型图采用统一的视觉语言：
- 卡片用 `0.5px` 浅边框 + 圆角，**无阴影**
- 工具栏、Tab、列表项的图标用 emoji（🖼 📤 ⚙ 📁 📄 💻 📅）而非 Material Icon
- 输入框用 surface2 圆角容器内嵌无边框 input
- emoji 与文字间距 4px（不是 6px）

代码里仍然用 Material Icon + 圆角 3px + light 模式阴影，与原型不一致。本次集中修复 8 处细节。

## 修复内容

| # | 位置 | 原状 | 修复 |
|---|------|------|------|
| 1 | `settings_screen.dart` `_SettingsCard` | light 模式阴影 + 无边框 | 移除阴影 + 加 `0.5px` `dividerColor` 边框 |
| 2 | `album_screen.dart` `_PhotoCell` | light 模式有 `BoxShadow` | 移除阴影；视频标记从 `Icons.play_circle_fill` 改为右下角小方块 + ▶ |
| 3 | `widgets/bottom_tab_bar.dart` `BottomTabItem` | `IconData icon` 必填 | 加 `emoji` 字段支持；底部 TabBar 改用 🖼/📤/⚙ |
| 4 | `connect_screen.dart` `_buildDeviceList` | `ListTile` + Material Icon | 改为带 💻 方块 + 设备名 + IP + 绿点的自定义行 |
| 5 | `album_screen.dart` `_IconButton` + 工具栏 | `Icons.folder` | 📁 emoji；扩展 `_IconButton` 支持 `emoji` 字段 |
| 6 | `widgets/tablet_sidebar.dart` 日期项 | `Icons.calendar_today_outlined` | 📄 emoji |
| 7 | `connect_screen.dart` `_buildManualEntry` | 双 `TextField` + `OutlineInputBorder` | surface2 圆角 10 容器内嵌无边框 input，🟢 0.5px 边框 |
| 8 | `pairing_code_screen.dart` 6 位配对码 | 40 宽方框 + 20px 字 + OutlineBorder | 44x52 + 1.5px 边框 + surface2 背景 + 22px w600 字 |

`album_screen.dart` 中 `_OutlineButton` 内 emoji↔text 间距 6 → 4，与原型一致。

## 关键改动文件

- `blurarc_app/lib/widgets/bottom_tab_bar.dart` — `BottomTabItem` 加 `emoji` 字段
- `blurarc_app/lib/widgets/tablet_sidebar.dart` — 日期项 emoji
- `blurarc_app/lib/screens/settings_screen.dart` — `_SettingsCard` 边框
- `blurarc_app/lib/screens/album_screen.dart` — `_PhotoCell` 阴影 / 视频标记 / `_IconButton` emoji / 工具栏 📁 / date 按钮间距
- `blurarc_app/lib/screens/connect_screen.dart` — 设备列表 / 手动输入框
- `blurarc_app/lib/screens/pairing_code_screen.dart` — 6 位配对码框

## 验证

```bash
cd f:\AI\Frame_Album\blurarc_app; flutter analyze
# No issues found! (ran in 5.4s)
```

`flutter analyze` 0 错 0 警告。手机/平板模拟器热更新后目视与原型一致（边框、emoji、间距、surface2 输入框）。
