# 2026-06-22 Flutter UI 与原型图对齐（重做三屏 + 主题统一）

## 背景

之前 `blurarc_app/` 实现了一个三 Tab 主页（相册/上传/设置），但实际效果与
`docs/prototypes/tablet/tablet-app-v3-light.html`（及 dark 模式）差异较大：
- 上传 Tab 没有大虚线框 dropzone，底部按钮样式不对
- 设置 Tab 没有 settings-card 包裹，主题选择不是 radio-btn 风格
- 主页 AppBar 用系统 Material 默认，不够品牌化

本次按原型图重做三屏 + 统一主题样式，亮色/暗色/手机均对齐。

## 主要改动

### 1. 主题系统统一（[colors.dart](../../blurarc_app/lib/theme/colors.dart) + [app_theme.dart](../../blurarc_app/lib/theme/app_theme.dart)）

- **新增激活态颜色**：`darkBgCardActive` / `lightBgCardActive`（背景 + 透明度 0x14）
- **新增主色 hover**：`darkPrimaryHover` (0xFF0891B2)
- **新增危险色**：`darkDanger` / `lightDanger` (0xFFdc2626)
- **文字色**：主/次/三级文字三个等级（dark: 0xFFe8f0f5 / 0xFF8aa0b0 / 0xFF506070）
- **AppBar**：透明背景、居中标题、无阴影
- **Card 边框**：0.5px
- **文本样式**：与原型图色值/字号匹配

### 2. ThemeProvider 主题名称（[theme_provider.dart](../../blurarc_app/lib/services/theme_provider.dart)）

- 新增 `label` getter，返回中文："跟随系统" / "浅色" / "深色"
- 修复了之前误删的 `_toString` 静态方法（用于持久化存储）

### 3. 新建 [BottomTabBar](../../blurarc_app/lib/widgets/bottom_tab_bar.dart)

- 自定义底部 Tab 栏，高度 52px（平板）/ 56px（手机）
- icon + 文字垂直排列
- 激活态顶部指示条 + 主色文字
- 顶部 0.5px divider 分隔

### 4. 新建 [PhotoSectionWithPhotos](../../blurarc_app/lib/models/photo_section_with_photos.dart)

- 数据模型：month + display + count + 照片列表 + hasMorePhotos
- 对接后端新端点 `/api/mobile/photos/all` 的连续网格数据结构

### 5. 重写 [AlbumScreen](../../blurarc_app/lib/screens/album_screen.dart)

- 主区域改为**连续滚动的照片网格**，按月分组
- 每个 section 顶部有 month header（如 "2026年6月"）
- 工具栏带"📅 跳转月份 ▼"按钮
- 平板：5列网格 + 侧栏；手机：3列网格
- 间距：平板 3px / 手机 2px
- 月份跳转后通过 ScrollController + GlobalKey 滚动到对应 section

### 6. 重写 [UploadScreen](../../blurarc_app/lib/screens/upload_screen.dart)

- **大虚线框 dropzone**：36px 垂直 padding + 2px dashed 边框 + icon + 文字

## 模拟器验证发现 Bug

### 首页缩略图加载失败，点开大图正常

**根因**：`CachedNetworkImage` 是裸 HTTP 请求，**不走 Dio 拦截器**，
Authorization header 不会自动注入 → 后端 `/api/mobile/thumbnail` 返回 401
→ `errorWidget` 显示破图。

**修复**（[album_screen.dart](../../blurarc_app/lib/screens/album_screen.dart#L591-L605)）：
`_resolveThumbUrl` 拼上 `?token=xxx` 兜底（后端
`mobile_access_server._extract_token` 已经有 query 读取 fallback）。
- 点击触发 `pickMultiImage` + `pickVideo` 多选
- **底部 fixed 按钮区**：次按钮 "全部取消" (Outlined) + 主按钮 "开始上传" (Filled, flex: 2)
- 上传中按钮替换为 LinearProgressIndicator
- 完成 SnackBar 提示

### 7. 重写 [SettingsScreen](../../blurarc_app/lib/screens/settings_screen.dart)

- 所有设置项用 `_SettingsCard` 容器包裹（亮色模式带轻微阴影）
- **连接信息卡片**：设备名称 + Token (截断) + 电脑地址
- **主题选择卡片**：3 个 radio-btn（跟随系统 / 浅色 / 深色），选中态主色高亮
- **仅 Wi-Fi 上传卡片**：自定义 toggle 开关（44x26），持久化到 SharedPreferences
- **关于卡片**：版本号
- **断开连接按钮**：危险色（红）描边按钮，点击弹确认对话框

### 8. 重写 [HomePage](../../blurarc_app/lib/screens/home_page.dart)

- 自定义 AppBar：toolbarHeight 52px + 居中 BlurArcLogoWithText
- `IndexedStack` 保留三个 Tab 状态
- 切换到非相册 Tab 时侧栏自动隐藏（由 AlbumScreen 内部实现，不影响其他页）
- 监听 `api.onDisconnected` 回调，连接断开时显示重连 UI

### 9. 修复 ApiClient token getter（[api_client.dart](../../blurarc_app/lib/services/api_client.dart)）

- 新增 `String? get token => _token;` 供 SettingsScreen 显示

## 验证

```bash
flutter analyze
# No issues found! (ran in 5.6s)
```

## 待优化

- [ ] 在真机/模拟器上跑一遍，截图对比原型图（亮/暗/手机/平板 4 个版本）
- [ ] 修复 UploadScreen 里 `pickVideo` 多次弹窗问题（应合并到 picker）
- [ ] TabletSidebar 折叠/展开动效
