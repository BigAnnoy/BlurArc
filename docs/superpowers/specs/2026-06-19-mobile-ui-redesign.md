# 技术实现方案：移动端 UI 重设计（Problem 3）

**版本：** v1.0
**日期：** 2026-06-19
**状态：** 待实现
**关联原型：** `docs/prototypes/mobile/mobile-app-v3-dark.html`, `docs/prototypes/mobile/mobile-app-v3-light.html`, `docs/prototypes/tablet/tablet-app-v3-dark.html`, `docs/prototypes/tablet/tablet-app-v3-light.html`

---

## 一、目标与范围

### 目标
根据 HTML 原型重新实现 Flutter App（blurarc_app）的 UI，使其与桌面端设计语言一致（暗色主题 #0c1117/#151d26/#22D3EE），同时针对手机和平板不同屏幕尺寸做自适应布局。

### 涉及页面
| 页面 | 手机 | 平板 |
|------|------|------|
| 相册（Album） | 底部 Tab + 日期跳转 + 文件夹入口 | 左侧边栏（仅相册页）+ 双指缩放 |
| 上传（Upload） | 底部 Tab | 全屏，无侧栏 |
| 设置（Settings） | 底部 Tab | 全屏，无侧栏 |

---

## 二、后端 API 变更

### 新增端点

#### `GET /api/mobile/photos/sections`
按月份分组返回照片列表，支持分页。

**请求参数：**
```
?page=1&page_size=60
```

**响应：**
```json
{
  "sections": [
    {
      "month": "2026-06",
      "display": "2026年6月",
      "count": 128,
      "photos": [
        {
          "path": "/albums/2026/2026-06/IMG_001.jpg",
          "thumbnail": "/api/mobile/thumbnail?path=...",
          "is_video": false,
          "duration": null
        }
      ]
    },
    {
      "month": "2026-05",
      "display": "2026年5月",
      "count": 96,
      "photos": [...]
    }
  ],
  "has_more": true,
  "available_months": ["2026-06", "2026-05", "2026-04", ...]
}
```

**实现说明：**
- 后端从数据库按 `date_taken` 或文件修改时间分组
- `available_months` 用于日历面板渲染（有照片的月份）
- 分页以 section 为单位，每次返回 N 个 section

#### `GET /api/mobile/folders`
返回相册目录的文件夹列表（用于文件夹视图）。

**请求参数：**
```
?path=/albums/2026  (可选，不传返回根目录)
```

**响应：**
```json
{
  "current_path": "/albums/2026",
  "parent_path": "/albums",
  "folders": [
    {"name": "2026-06", "path": "/albums/2026/2026-06", "photo_count": 128},
    {"name": "2026-05", "path": "/albums/2026/2026-05", "photo_count": 96}
  ],
  "breadcrumb": [
    {"name": "相册根目录", "path": "/albums"},
    {"name": "2026", "path": "/albums/2026"}
  ]
}
```

---

## 三、Flutter App 前端实现

### 3.1 项目结构（更新后）

```
lib/
├── main.dart                          # 入口，主题初始化
├── models/
│   ├── photo.dart                     # Photo model（已有，需扩展）
│   ├── album_tree.dart                # Tree model（已有）
│   ├── photo_section.dart             # NEW: 按月分组的 Section model
│   └── folder_entry.dart              # NEW: 文件夹入口 model
├── screens/
│   ├── connect_screen.dart             # 已有，不变
│   ├── pairing_code_screen.dart        # 已有，不变
│   ├── home_page.dart                 # 重构：Mobile/Tablet 布局路由
│   ├── album_screen.dart              # 重构：新 UI
│   ├── folder_screen.dart             # NEW: 文件夹视图
│   ├── upload_screen.dart             # 重构：真实上传功能
│   ├── settings_screen.dart           # 重构：新设计
│   └── photo_preview_screen.dart      # 已有，不变
├── widgets/
│   ├── photo_card.dart                # 已有，不变
│   ├── responsive_layout.dart         # 已有，不变
│   ├── tree_view.dart                 # 已有，平板上复用
│   ├── month_calendar_sheet.dart      # NEW: 手机版日历底部面板
│   ├── date_jump_panel.dart           # NEW: 平板版日期跳转面板
│   ├── photo_grid.dart                # 重构：支持双指缩放
│   └── upload_progress.dart          # 已有，不变
├── services/
│   ├── api_client.dart                # 扩展：新增 API 调用
│   └── theme_provider.dart            # NEW: 主题管理（dark/light/system）
└── theme/
    ├── app_theme.dart                 # NEW: 主题定义（dark + light）
    └── colors.dart                    # NEW: 设计色值常量
```

---

### 3.2 主题系统

#### `lib/theme/colors.dart`
```dart
import 'package:flutter/material.dart';

class AppColors {
  // Dark theme (primary)
  static const darkBgPage = Color(0xFF0c1117);
  static const darkBgCard = Color(0xFF151d26);
  static const darkBgCardHover = Color(0xFF1a2533);
  static const darkBorder = Color(0xFF1c2836);
  static const darkPrimary = Color(0xFF22D3EE);

  // Light theme
  static const lightBgPage = Color(0xFFf5f7fa);
  static const lightBgCard = Color(0xFFFFFFFF);
  static const lightBorder = Color(0xFFe2e8f0);
  static const lightPrimary = Color(0xFF0891b2);
}
```

#### `lib/theme/app_theme.dart`
- `AppTheme.dark()` — 暗色主题，参考桌面端
- `AppTheme.light()` — 亮色主题
- 支持 `ThemeMode.system` / `.dark` / `.light`

#### `lib/services/theme_provider.dart`
- 使用 `shared_preferences` 持久化用户选择
- `ChangeNotifier` + `Provider` 通知全局主题变更

---

### 3.3 手机版 UI 实现

#### 整体布局：`home_page.dart`
```
Scaffold(
  body: IndexedStack(
    index: _currentTab,  // 0=相册, 1=上传, 2=设置
    children: [
      AlbumTab(),
      UploadTab(),
      SettingsTab(),
    ],
  ),
  bottomNavigationBar: BottomNavigationBar(
    currentIndex: _currentTab,
    onTap: (i) => setState(() => _currentTab = i),
    items: [
      BottomNavigationBarItem(icon: Icon(Icons.photo), label: '相册'),
      BottomNavigationBarItem(icon: Icon(Icons.upload), label: '上传'),
      BottomNavigationBarItem(icon: Icon(Icons.settings), label: '设置'),
    ],
  ),
)
```

#### `AlbumTab`（相册 Tab）
```
Column(
  children: [
    // 顶部工具栏（仅在相册 tab 显示）
    AlbumToolbar(
      onDateJump: () => showMonthCalendar(context),
      onFolder: () => Navigator.push(FolderScreen()),
    ),
    // 照片网格（按月份分组）
    Expanded(
      child: PhotoSectionList(
        sections: _sections,
        onPhotoTap: (photo) => Navigator.push(PhotoPreviewScreen()),
      ),
    ),
  ],
)
```

**`AlbumToolbar`**：
- 「📅 2026年6月 ▾」按钮 → 弹出日历底部面板
- 「📁」按钮 → 跳转到文件夹视图

**`MonthCalendarSheet`**（日历底部面板）：
- 年份切换按钮（‹ 2026 ›）
- 4×3 月份网格，`available_months` 有照片的月份高亮
- 点击月份 → 滚动到对应 section

#### `FolderScreen`（文件夹视图）
```
Scaffold(
  appBar: AppBar(
    leading: BackButton(),
    title: Text('文件夹'),
  ),
  body: Column(
    children: [
      BreadcrumbBar(breadcrumb: _breadcrumb),
      Expanded(
        child: ListView(
          children: _folders.map((f) => FolderListTile(
            name: f.name,
            count: f.photoCount,
            onTap: () => openFolder(f.path),
          )).toList(),
        ),
      ),
    ],
  ),
)
```

---

### 3.4 平板版 UI 实现

#### 整体布局：`home_page.dart`（Tablet）
```
Row(
  children: [
    // 左侧边栏（仅在相册 tab 显示）
    if (_currentTab == 0 && !_sidebarCollapsed)
      Sidebar(
        sections: _sections,
        onSelect: _scrollToSection,
        onCollapse: () => setState(() => _sidebarCollapsed = true),
      ),
    // 展开按钮（侧栏收起时显示）
    if (_currentTab == 0 && _sidebarCollapsed)
      ExpandSidebarButton(
        onTap: () => setState(() => _sidebarCollapsed = false),
      ),
    // 主内容区
    Expanded(
      child: IndexedStack(
        index: _currentTab,
        children: [AlbumContent(), UploadContent(), SettingsContent()],
      ),
    ),
  ],
)
```

#### `Sidebar`
```
SizedBox(
  width: 240,
  child: Column(
    children: [
      SidebarHeader(title: '相册 · $_total 张'),
      Expanded(
        child: ListView(
          children: _sections.map((s) => SidebarItem(
            label: s.display,
            count: s.count,
            active: s.month == _activeMonth,
            onTap: () => onSelect(s.month),
          )).toList(),
        ),
      ),
      // 收起按钮（在侧栏底部）
      SidebarFooter(
        collapsed: false,
        onToggle: onCollapse,
      ),
    ],
  ),
)
```

#### 双指缩放（Pinch-to-Zoom）
在 `PhotoGrid` widget 中使用 `GestureDetector` + `onScaleUpdate`：

```dart
class PhotoGrid extends StatefulWidget {
  @override
  _PhotoGridState createState() => _PhotoGridState();
}

class _PhotoGridState extends State<PhotoGrid> {
  int _columns = 5;  // 平板默认 5 列

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onScaleUpdate: (details) {
        // 双指缩放改变列数
        if (details.scale < 0.95) {
          setState(() => _columns = (_columns + 1).clamp(3, 8));
        } else if (details.scale > 1.05) {
          setState(() => _columns = (_columns - 1).clamp(3, 8));
        }
      },
      child: GridView.builder(
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: _columns,
          ...
        ),
        ...
      ),
    );
  }
}
```

> **注意**：Flutter 的 `onScaleUpdate` 直接给出缩放比例。实际实现可以用 `onScaleStart` 记录初始 columns，在 `onScaleUpdate` 里根据 scale 差值调整，避免过于敏感。

#### 日期跳转面板（平板）
点击工具栏「📅 跳转月份 ▾」按钮 → 弹出 `DateJumpPanel`（Overlay 或 Dialog）：

```
DateJumpPanel(
  currentYear: _currentYear,
  availableMonths: _availableMonths,
  onSelect: (year, month) => _scrollToMonth(year, month),
)
```

---

### 3.5 上传页面实现

#### `UploadScreen`（重构）
```
Column(
  children: [
    // 文件选择区域
    UploadDropzone(
      onPickFiles: () async {
        final result = await FilePicker.platform.pickFiles(
          allowMultiple: true,
          type: FileType.media,  // 图片 + 视频
        );
        if (result != null) addToUploadQueue(result.files);
      },
    ),
    // 上传列表
    Expanded(
      child: ListView(
        children: _uploadQueue.map((item) => UploadListItem(
          file: item.file,
          progress: item.progress,
          status: item.status,
        )).toList(),
      ),
    ),
    // 操作按钮
    UploadActions(
      onStart: _startUpload,
      onCancelAll: _clearQueue,
    ),
  ],
)
```

**上传逻辑**：
1. 用户选择文件 → 加入 `_uploadQueue`（本地）
2. 点击「开始上传」→ 逐个调用 `apiClient.uploadFile()`
3. 用 `Dio` 的 `onSendProgress` 回调更新进度
4. 全部完成后提示，并可选刷新相册

---

### 3.6 设置页面实现

#### `SettingsScreen`（重构）
```
ListView(
  children: [
    SettingsSection(title: '设备信息', children: [
      SettingsItem(label: '设备名称', value: _deviceName, onEdit: _editDeviceName),
      SettingsItem(label: 'Token', value: _tokenShort, onTap: _copyToken),
    ]),
    SettingsSection(title: '显示', children: [
      SettingsThemePicker(
        current: _themeMode,
        onChange: (mode) => themeProvider.setTheme(mode),
      ),
    ]),
    SettingsSection(title: '上传', children: [
      SettingsSwitch(label: '仅在 Wi-Fi 下上传', value: _wifiOnly, onChange: _setWifiOnly),
    ]),
    SettingsSection(children: [
      DangerButton(label: '断开连接', onTap: _confirmDisconnect),
    ]),
  ],
)
```

---

## 四、后端实现细节

### 4.1 `GET /api/mobile/photos/sections`

**文件：** `backend/mobile_access_server.py`

```python
@app.route('/api/mobile/photos/sections')
@token_required
def get_photo_sections():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 60, type=int)

    # 查询数据库，按月份分组
    conn = get_db_connection()
    # 获取所有有照片的月份
    months_rows = conn.execute("""
        SELECT DISTINCT strftime('%Y-%m', date_taken) as month
        FROM photos
        WHERE date_taken IS NOT NULL
        ORDER BY month DESC
    """).fetchall()

    available_months = [row['month'] for row in months_rows]

    # 分页获取 sections
    start = (page - 1) * page_size
    end = start + page_size
    sections = []

    for month_str in available_months[start:end]:
        year, month = month_str.split('-')
        photos_rows = conn.execute("""
            SELECT path, is_video, duration
            FROM photos
            WHERE strftime('%Y-%m', date_taken) = ?
            ORDER BY date_taken DESC, path
            LIMIT 100
        """, (month_str,)).fetchall()

        sections.append({
            'month': month_str,
            'display': f'{year}年{int(month)}月',
            'count': len(photos_rows),
            'photos': [{'path': r['path'], ...} for r in photos_rows],
        })

    return jsonify({
        'sections': sections,
        'has_more': end < len(available_months),
        'available_months': available_months,
    })
```

### 4.2 `GET /api/mobile/folders`

```python
@app.route('/api/mobile/folders')
@token_required
def get_folders():
    path = request.args.get('path', '').strip()
    # 安全校验：防止路径遍历
    if not _is_path_safe(path):
        return jsonify({'error': 'invalid path'}), 400

    # 列出该路径下的子文件夹
    # 参考 _get_tree_impl 的实现
    ...
```

---

## 五、实施步骤

### Phase 1：后端 API（预计 1 天）
- [ ] 实现 `GET /api/mobile/photos/sections`
- [ ] 实现 `GET /api/mobile/folders`
- [ ] 单元测试

### Phase 2：主题系统（预计 0.5 天）
- [ ] 创建 `lib/theme/colors.dart`
- [ ] 创建 `lib/theme/app_theme.dart`
- [ ] 创建 `lib/services/theme_provider.dart`
- [ ] 在 `main.dart` 接入主题

### Phase 3：手机版相册 Tab（预计 2 天）
- [ ] 重构 `home_page.dart`（底部 Tab 导航）
- [ ] 实现 `AlbumToolbar`
- [ ] 实现 `PhotoSectionList`（分组网格）
- [ ] 实现 `MonthCalendarSheet`（日历底部面板）
- [ ] 实现 `FolderScreen`（文件夹视图）

### Phase 4：平板版布局（预计 1.5 天）
- [ ] 实现 `Sidebar` widget
- [ ] 实现侧栏收起/展开逻辑
- [ ] 实现 `PhotoGrid` 双指缩放
- [ ] 实现 `DateJumpPanel`

### Phase 5：上传页面（预计 1 天）
- [ ] 重构 `UploadScreen`
- [ ] 接入 `file_picker` 插件
- [ ] 实现上传队列 + 进度显示
- [ ] 接入 `apiClient.uploadFile()`

### Phase 6：设置页面（预计 0.5 天）
- [ ] 重构 `SettingsScreen`
- [ ] 接入主题切换
- [ ] 接入 Wi-Fi 设置

### Phase 7：联调测试（预计 1 天）
- [ ] 真机调试（Android）
- [ ] 验证所有 API 端点
- [ ] 修复 bug

---

## 六、依赖插件

在 `pubspec.yaml` 中添加/确认：

```yaml
dependencies:
  flutter:
    sdk: flutter
  dio: ^5.4.0              # 已有，HTTP 客户端
  shared_preferences: ^2.2.2 # 已有，本地存储
  provider: ^6.1.1          # 主题状态管理
  file_picker: ^8.0.0        # 文件选择
  flutter_spinkit: ^5.2.0    # 加载动画（可选）
```

---

## 七、关键设计决策

1. **分组方式**：按 `date_taken` 的年月分组，与桌面端一致
2. **分页策略**：以 section（月份）为单位分页，每次加载 N 个月的数据
3. **主题持久化**：使用 `shared_preferences` 存储用户主题偏好
4. **双指缩放**：平板专属，手机用底部 Tab 导航不需要此功能
5. **侧栏显示逻辑**：仅在相册 Tab 显示，其他 Tab 全屏展示

---

## 八、验收标准

- [ ] 手机版：底部 3 Tab 导航流畅，相册页日期跳转可用
- [ ] 手机版：文件夹视图可浏览，面包屑导航正确
- [ ] 平板版：侧栏仅在相册页显示，可收起/展开
- [ ] 平板版：双指缩放调整网格列数（3~8 列）
- [ ] 主题切换：dark/light/system 三种模式正常切换
- [ ] 上传功能：可选择文件、显示进度、完成后提示
- [ ] 设置页面：显示设备信息、可切换主题、可断开连接
- [ ] 所有现有功能（配对、浏览）不被破坏
