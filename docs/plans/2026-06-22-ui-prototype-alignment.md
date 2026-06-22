# 手机/平板 UI 与原型对齐

**日期：** 2026-06-22
**状态：** 待实施
**影响范围：** Flutter App 全部三个 Tab + HomePage + 后端新增 1 个端点

## 原型文件

| 平台 | 亮色 | 暗色 |
|------|------|------|
| 平板 | `tablet/tablet-app-v3-light.html` | `tablet/tablet-app-v3-dark.html` |
| 手机 | `mobile/mobile-app-v3-light.html` | `mobile/mobile-app-v3-dark.html` |

## 主题色（统一）

| 模式 | primary | bg-page | bg-card | border | text-primary | text-secondary | text-tertiary |
|------|---------|---------|---------|--------|--------------|----------------|---------------|
| 亮色 | `#0891b2` | `#f5f7fa` | `#ffffff` | `#e2e6ed` | `#1a2332` | `#5a6a80` | `#9aa5b5` |
| 暗色 | `#22d3ee` | `#0c1117` | `#151d26` | `#1c2836` | `#e8f0f5` | `#8aa0b0` | `#506070` |

**主色策略：**
- 亮色：青蓝 `#0891b2`（cyan-700）
- 暗色：青色 `#22d3ee`（cyan-400）
- 当前 AppColors.lightPrimary/darkPrimary 已是这个值，不变

## 主题模式命名

| 当前 | 原型（中文） |
|------|--------------|
| 自动 | 跟随系统 |
| 亮色 | 浅色 |
| 暗色 | 深色 |

## 三大差异（核心）

### 差异 #1：相册 Tab 内容（最关键）

**原型：**
- 主区域是**连续滚动的照片网格**
- 按月分组（section header "2026年6月"），每组下方 5 列（平板）/ 3 列（手机）的照片网格
- 向下滚动无限加载更多月份
- 工具栏：标题 + 右侧"📅 跳转月份 ▼" 按钮
- 点击月份按钮 → 弹层显示日历（年份导航 + 4x3 月份网格，带照片数量徽标）
- 滚动到底部 section header 时，左侧 sidebar 自动高亮对应月份

**当前实现：**
- 主区域是**月份列表**（ListTile）
- 点击月份 → 跳转 `MonthPhotoScreen` 单独加载该月照片
- 工具栏：仅 "相册" 标题 + 文件夹图标
- 没有"跳转月份"功能
- `MonthCalendarSheet` 组件存在但**没被任何地方调用**

**修复方案：**

1. **后端新增端点** `GET /api/mobile/photos/all` ：
   - 返回按月分组的所有照片，分页（每页 N 个月）
   - 字段：`{ sections: [{ month, display, count, photos: [{path, thumbnail, is_video, filename, taken_at}] }], has_more, available_months }`
   - 不强制 `media_date` 必须有；无日期照片归到 `no-date` 虚拟组

2. **AlbumScreen 整体重做：**
   - 改为连续 `CustomScrollView` 模式
   - 每个 section 一个 `SliverStickyHeader`（可选）或 `SliverList`
   - 工具栏加"跳转月份"按钮 → `MonthCalendarSheet.show()`
   - 平板 5 列网格，手机 3 列
   - 双指缩放切换列数（可选，先不实现；3-5 列固定）
   - 点击照片 → `PhotoPreviewScreen`

3. **保留** `MonthPhotoScreen` 文件但停用（兼容性），后续可删除

4. **删除** `month_calendar_sheet.dart` 的"孤儿"状态，让它真正被 `AlbumScreen` 调用

### 差异 #2：Tab 切换时侧栏隐藏

**原型：**
- 切换到"上传"或"设置"时，整个侧栏完全隐藏（`display: none`）
- 侧栏只在"相册" Tab 显示

**当前实现：**
- 侧栏在三个 Tab 都显示（错误）

**修复方案：**
- `AlbumScreen` 内置侧栏（已有），不需要外部状态
- 检查并确保：切换到 UploadScreen/SettingsScreen 时，侧栏不出现在 mainArea 中

### 差异 #3：底部 Tab 样式

**原型：**
- 3 个 Tab：相册 / 上传 / 设置
- 每个 Tab：icon + 文字（垂直排列）
- 选中：青色 + 顶部 2px 青色指示条
- 高 52px（手机 56px），无 Material NavigationBar 默认阴影

**当前实现：**
- `NavigationBar`（Material 3 风格）→ 有 FAB 槽位、不同的高亮动画

**修复方案：**
- 不用 `NavigationBar`，改用自定义 `BottomNavigationBar` 或自绘 `Row` 容器
- 52px（平板）/ 56px（手机）高
- 选中样式：顶部 2px 青色条

## 实施清单（按文件）

| # | 文件 | 改动 |
|---|------|------|
| 1 | `backend/mobile_access_server.py` | 新增 `/api/mobile/photos/all` 端点 |
| 2 | `blurarc_app/lib/services/api_client.dart` | 新增 `getAllPhotosBySection(page)` |
| 3 | `blurarc_app/lib/widgets/photo_grid_section.dart` | **新增** - 单个月份 section 渲染组件 |
| 4 | `blurarc_app/lib/widgets/photo_grid_cell.dart` | **新增** - 单个 photo cell |
| 5 | `blurarc_app/lib/screens/album_screen.dart` | **重写** - 连续网格布局 |
| 6 | `blurarc_app/lib/widgets/tablet_sidebar.dart` | 调整：底部按钮改纯箭头 + 同步选中态 |
| 7 | `blurarc_app/lib/screens/home_page.dart` | AppBar 改 logo 居中样式 + 侧栏显隐交给子页面 |
| 8 | `blurarc_app/lib/widgets/bottom_tab_bar.dart` | **新增** - 自定义底部 Tab 栏 |
| 9 | `blurarc_app/lib/screens/upload_screen.dart` | 重做 dropzone 样式 + 主次按钮 |
| 10 | `blurarc_app/lib/screens/settings_screen.dart` | 重做 settings-card 包裹 + radio-btn + 危险按钮 |
| 11 | `blurarc_app/lib/services/theme_provider.dart` | 命名：跟随系统/浅色/深色 |
| 12 | `blurarc_app/lib/theme/app_theme.dart` | 调整颜色细节（page/card/border 等） |
| 13 | `blurarc_app/lib/theme/colors.dart` | 同步原型的具体色值 |

## 验证

- `flutter analyze` 通过
- 真机/模拟器跑通：登录 → 相册连续网格 → 跳转月份弹层 → 切换 Tab
- 截图对比原型

## 后续可选（不在本次范围）

- 照片双指缩放切换列数
- 平板侧栏双指拖动调宽度
- 文件夹视图（FolderScreen）UI 调整
- 照片预览页 UI 调整
