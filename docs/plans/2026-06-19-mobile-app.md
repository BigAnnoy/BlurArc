# Mobile App 原型到位实现计划

**Goal:** 将 Flutter App 实现为与 HTML 原型完全一致的手机端 UI
**Architecture:** 共享 AppBar（HomePage）+ IndexedStack（3 tab）+ 各 Tab 仅提供内容区域；连接页面独立 2 步流程
**Tech Stack:** Flutter 3.44 + Dart + Provider + shared_preferences

---

## 文件结构规划

| 文件 | 操作 | 职责 |
|------|------|------|
| `lib/main.dart:27-31` | Modify | 启动页从 ConnectScreen 保持不变 |
| `lib/screens/home_page.dart` | Modify | 添加共享 AppBar（logo + "Blur Arc"），子页不再自带 AppBar |
| `lib/screens/album_screen.dart` | Modify | 移除自身 AppBar/Scaffold，工具栏作为内容一部分 |
| `lib/screens/upload_screen.dart` | Modify | 移除自身 AppBar/Scaffold，匹配原型布局 |
| `lib/screens/settings_screen.dart` | Modify | 移除自身 AppBar/Scaffold |
| `lib/screens/connect_screen.dart` | Modify | 匹配原型 2 步流程：步骤指示器 + 设备列表 + 手动输入 |
| `lib/screens/pairing_code_screen.dart` | Modify | 匹配原型：居中 logo + 步骤指示 + 配对码输入 |
| `lib/widgets/blur_arc_logo.dart` | 不变 | 已匹配 PC 版设计（CustomPaint 弧线 logo） |
| `lib/theme/app_theme.dart` | 不变 | 色彩已与原型一致 |
| `lib/theme/colors.dart` | 不变 | 色值已与原型一致 |

---

## 覆盖率分析

| 原型要素 | 当前状态 | 需改进 |
|---------|---------|--------|
| 状态栏（时间+信号） | Flutter 系统自带 | 无需处理 |
| 标题栏（logo + "Blur Arc"） | 各页面独立 AppBar | 改为 HomePage 共享 AppBar |
| 相册 Tab — 日期选择工具栏 | 在 AppBar bottom | 移到内容区顶部 |
| 相册 Tab — 分组照片网格 | ✅ 已实现 | 不变 |
| 相册 Tab — 文件夹按钮 | ✅ 已实现 | 不变 |
| 上传 Tab — 选择照片区域 | ✅ 已实现 | 移除 AppBar |
| 上传 Tab — 上传进度列表 | ✅ 已实现 | 不变 |
| 设置 Tab — 连接信息 | ✅ 已实现 | 移除 AppBar |
| 设置 Tab — 主题切换 | ✅ 已实现 | 不变 |
| 设置 Tab — Wi-Fi 开关 | ✅ 已实现 | 不变 |
| 设置 Tab — 断开连接 | ✅ 已实现 | 不变 |
| 底部导航栏 | ✅ 已实现 | 已匹配 |
| 日历底部弹出面板 | ✅ month_calendar_sheet.dart | 不变 |
| 全屏照片预览 | ✅ photo_preview_screen.dart | 不变 |
| 连接页 — 步骤指示器 | ❌ 缺失 | 新增 |
| 连接页 — 设备发现列表 | ✅ 已实现 | 微调样式 |
| 连接页 — 手动输入 IP:端口 | ✅ 已实现 | 微调样式 |
| 配对码页 — 步骤指示器 | ❌ 缺失 | 新增 |
| 配对码页 — 6 位数字输入 | ✅ 已实现 | 不变 |

---

### Task 1: 重构 HomePage — 添加共享 AppBar

**Files:**
- Modify: `lib/screens/home_page.dart` (全文件)

移除各子页面的独立 Scaffold/AppBar，改由 HomePage 提供共享 AppBar。

- [ ] **Step 1: 修改 HomePage 添加共享 AppBar**
```dart
// home_page.dart — 在 build() 中：
return Scaffold(
  appBar: AppBar(
    title: const BlurArcLogoWithText(logoSize: 24, fontSize: 14),
    centerTitle: true,
    elevation: 0,
    scrolledUnderElevation: 0.5,
  ),
  body: IndexedStack(
    index: _currentIndex,
    children: _pages,
  ),
  bottomNavigationBar: NavigationBar(
    // ... 保持不变
  ),
);
```

- [ ] **Step 2: 验证编译**
Run: `cd blurarc_app && flutter build apk --debug`
预期：编译通过（但子页面还有 AppBar，视觉上会有双重 AppBar）

---

### Task 2: 移除 AlbumScreen 自身 AppBar，工具栏移入内容区

**Files:**
- Modify: `lib/screens/album_screen.dart:215-261`

AlbumScreen 目前有独立 Scaffold + AppBar（带 bottom 工具栏）。改为：返回纯 Widget（无 Scaffold），工具栏作为 Column 第一行。

- [ ] **Step 1: 将 `_buildMobileLayout` 从返回 Scaffold 改为返回 Column**
```dart
// album_screen.dart — 手机布局改为：
Widget _buildMobileLayout() {
  final theme = Theme.of(context);
  return Column(
    children: [
      // 工具栏（日期 + 文件夹）
      _buildAlbumToolbar(theme),
      // 照片网格
      Expanded(child: _buildPhotoGrid()),
    ],
  );
}

Widget _buildAlbumToolbar(ThemeData theme) {
  return Padding(
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    child: Row(
      children: [
        Expanded(
          child: OutlinedButton.icon(
            onPressed: _showDatePicker,
            icon: const Icon(Icons.calendar_today, size: 16),
            label: Text(_displayMonth.isNotEmpty ? _displayMonth : '选择月份'),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              side: BorderSide(color: theme.dividerColor),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          width: 44,
          height: 44,
          child: OutlinedButton(
            onPressed: _openFolderView,
            style: OutlinedButton.styleFrom(
              padding: EdgeInsets.zero,
              side: BorderSide(color: theme.dividerColor),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
            child: const Icon(Icons.folder, size: 20),
          ),
        ),
      ],
    ),
  );
}
```

- [ ] **Step 2: 平板布局同步修改**
```dart
// album_screen.dart — _buildTabletLayout 中：
// 移除 AppBar，保留 Row(Sidebar + Expanded(Column(toolbar + grid)))
Widget _buildTabletLayout() {
  return Row(
    children: [
      if (!_sidebarCollapsed) TabletSidebar(...),
      if (_sidebarCollapsed) TabletSidebarExpandButton(...),
      Expanded(
        child: Column(
          children: [
            Row(
              children: [
                const BlurArcLogoWithText(logoSize: 24, fontSize: 14),
                const SizedBox(width: 16),
                Expanded(child: _buildAlbumToolbarCompact()),
              ],
            ),
            Expanded(child: _buildPhotoGrid(isTablet: true)),
          ],
        ),
      ),
    ],
  );
}
```

- [ ] **Step 3: AlbumScreen 在 HomePage 中注册方式不变**
HomePage 的 `_pages` 列表保持不变：
```dart
_pages = [
  AlbumScreen(api: widget.api),
  const UploadScreen(),
  SettingsScreen(api: widget.api),
];
```

- [ ] **Step 4: 验证**
Run: `cd blurarc_app && flutter build apk --debug`
预期：相册 Tab 显示共享 AppBar + 内嵌工具栏

---

### Task 3: 移除 UploadScreen 自身 AppBar

**Files:**
- Modify: `lib/screens/upload_screen.dart:23-155`

移除 Scaffold + AppBar，改为纯 Column 内容。

- [ ] **Step 1: UploadScreen 改为返回 Widget（非 Scaffold）**
```dart
// upload_screen.dart — build() 改为：
@override
Widget build(BuildContext context) {
  final theme = Theme.of(context);
  final api = widget.api;

  if (api == null || !api.isConnected) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.cloud_off, size: 48,
              color: theme.colorScheme.onSurface.withAlpha(80)),
          const SizedBox(height: 12),
          Text('未连接到电脑',
              style: TextStyle(
                  color: theme.colorScheme.onSurface.withAlpha(120))),
        ],
      ),
    );
  }

  // 返回 Column（内容同原 Scaffold body）
  final pendingCount = _items.where((i) => i.status == UploadStatus.pending).length;
  final doneCount = _items.where((i) => i.status == UploadStatus.done).length;

  return Column(
    children: [
      // 文件选择区域 + 统计 + 列表 + 底部操作
      // ... (同原 body 内容，去掉 Scaffold 外包装)
    ],
  );
}
```

- [ ] **Step 2: 清空按钮改为在内容区顶部显示**
原 AppBar 的 "清空" actions 移到上传列表上方或文件选择区旁边：
```dart
// 在文件选择区域上方添加一行：
if (_items.isNotEmpty && !_isUploading)
  Padding(
    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
    child: Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        TextButton(
          onPressed: _clearAll,
          child: Text('清空',
              style: TextStyle(color: theme.colorScheme.error)),
        ),
      ],
    ),
  ),
```

- [ ] **Step 3: 验证编译**
Run: `cd blurarc_app && flutter build apk --debug`

---

### Task 4: 移除 SettingsScreen 自身 AppBar

**Files:**
- Modify: `lib/screens/settings_screen.dart:14-82`

移除 Scaffold + AppBar，改为纯 ListView。

- [ ] **Step 1: SettingsScreen 改为返回 Widget（非 Scaffold）**
```dart
// settings_screen.dart — build() 改为返回 ListView：
@override
Widget build(BuildContext context) {
  final theme = Theme.of(context);
  final themeProvider = context.watch<ThemeProvider>();

  return ListView(
    children: [
      // === 连接信息 ===
      const _SectionHeader(title: '连接信息'),
      // ... 其余内容保持不变
    ],
  );
}
```

- [ ] **Step 2: 验证编译**
Run: `cd blurarc_app && flutter build apk --debug`

---

### Task 5: ConnectScreen — 匹配原型 2 步流程

**Files:**
- Modify: `lib/screens/connect_screen.dart` (全文件)

原型设计：
```
状态栏
标题栏（logo + Blur Arc）
━━━━━━━━━━━━━━━━━━
步骤 1/2：连接设备    ○ ●
────────────────────
  发现的设备
  ┌─────────────────────┐
  │ 💻 MyPC             │
  │    192.168.1.100:8900│
  └─────────────────────┘
  
  或手动输入
  IP 地址 [192.168.1.100] : 端口 [8900]
  ┌─────────────────────┐
  │       连接          │
  └─────────────────────┘
```

- [ ] **Step 1: 添加步骤指示器 + 调整布局**
```dart
// connect_screen.dart — 修改 Scaffold body 结构：
body: _checkingToken
    ? const Center(child: CircularProgressIndicator())
    : Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 步骤指示器
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 10, height: 10,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: theme.colorScheme.primary,
                ),
              ),
              Container(width: 40, height: 1, color: theme.dividerColor),
              Container(
                width: 10, height: 10,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: theme.dividerColor),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text('步骤 1/2：连接设备',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium),
          const SizedBox(height: 24),
          
          // 发现的设备
          if (_discovered.isNotEmpty) ...[
            const Text('发现的设备', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                itemCount: _discovered.length,
                itemBuilder: (context, index) => _buildDeviceCard(_discovered[index]),
              ),
            ),
          ],
          
          // 手动输入（始终显示在底部）
          const SizedBox(height: 16),
          const Text('或手动输入', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          _buildManualEntryRow(),
        ],
      ),
    );
```

- [ ] **Step 2: 重构设备卡片样式**
```dart
Widget _buildDeviceCard(DiscoveredService service) {
  return Card(
    margin: const EdgeInsets.only(bottom: 8),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(10),
      side: BorderSide(color: Theme.of(context).dividerColor),
    ),
    child: ListTile(
      leading: const Icon(Icons.computer, color: Color(0xFF22D3EE)),
      title: Text(service.name, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
      subtitle: Text('${service.host}:${service.port}', style: const TextStyle(fontSize: 13)),
      onTap: () => _onDeviceTap(service),
    ),
  );
}
```

- [ ] **Step 3: 手动输入改为横排 IP:端口**
```dart
Widget _buildManualEntryRow() {
  final hostController = TextEditingController();
  final portController = TextEditingController(text: '8900');
  
  return Column(
    children: [
      Row(
        children: [
          Expanded(
            child: TextField(
              controller: hostController,
              decoration: const InputDecoration(
                hintText: 'IP 地址',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              ),
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 8),
            child: Text(':', style: TextStyle(fontSize: 18)),
          ),
          SizedBox(
            width: 80,
            child: TextField(
              controller: portController,
              decoration: const InputDecoration(
                hintText: '8900',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              ),
              keyboardType: TextInputType.number,
            ),
          ),
        ],
      ),
      const SizedBox(height: 12),
      SizedBox(
        width: double.infinity,
        child: FilledButton(
          onPressed: () {
            final host = hostController.text.trim();
            final port = int.tryParse(portController.text.trim()) ?? 8900;
            if (host.isEmpty) return;
            _onDeviceTap(DiscoveredService(name: 'Manual', host: host, port: port));
          },
          child: const Text('连接'),
        ),
      ),
    ],
  );
}
```

- [ ] **Step 4: 验证编译**
Run: `cd blurarc_app && flutter build apk --debug`

---

### Task 6: PairingCodeScreen — 匹配原型 2 步布局

**Files:**
- Modify: `lib/screens/pairing_code_screen.dart:120-270`

原型第二页：
```
状态栏
标题栏（logo + Blur Arc）
━━━━━━━━━━━━━━━━━━
步骤 2/2：输入配对码    ○ ●
────────────────────
  🔗 等待 PC 确认
  请在 PC 端确认此设备的连接请求
  确认后会显示 6 位配对码
  
  [1][2][3][4][5][6]
  请在 PC 端确认后，输入显示的 6 位配对码
  
  [  返回  ] [ 确认配对 ]
```

- [ ] **Step 1: 添加步骤指示器**
```dart
// pairing_code_screen.dart — 在 Scaffold body 顶部添加：
body: Padding(
  padding: const EdgeInsets.all(24),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      // 步骤指示器
      Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 10, height: 10,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: Theme.of(context).dividerColor),
            ),
          ),
          Container(width: 40, height: 1, color: Theme.of(context).dividerColor),
          Container(
            width: 10, height: 10,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
        ],
      ),
      const SizedBox(height: 8),
      const Text('步骤 2/2：输入配对码',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 14)),
      const SizedBox(height: 24),
      
      // 原有内容...
    ],
  ),
);
```

- [ ] **Step 2: 添加返回/确认双按钮**
```dart
// 替换底部单一 FilledButton：
Row(
  children: [
    Expanded(
      child: OutlinedButton(
        onPressed: _isSubmitting ? null : () => Navigator.pop(context),
        child: const Text('返回'),
      ),
    ),
    const SizedBox(width: 12),
    Expanded(
      child: FilledButton(
        onPressed: _isSubmitting ? null : (_code.length == 6 ? _submitCode : null),
        child: const Text('确认配对'),
      ),
    ),
  ],
),
```

- [ ] **Step 3: 验证编译**
Run: `cd blurarc_app && flutter build apk --debug`

---

### Task 7: 全量编译验证 + UI 审查

- [ ] **Step 1: 全量编译**
Run: `cd blurarc_app && flutter build apk --debug`
预期：无错误通过

- [ ] **Step 2: 检查关键点**
  - HomePage AppBar 显示 logo + "Blur Arc"（居中）
  - 相册 Tab：工具栏在内容区顶部，不在 AppBar 中
  - 上传 Tab：无 AppBar，清空按钮在内容区
  - 设置 Tab：无 AppBar，列表正常显示
  - ConnectScreen：2 步指示器 + 设备卡片 + 手动输入
  - PairingCodeScreen：2 步指示器 + 双按钮

---

## 自审

1. **规格覆盖**
   - ✅ 状态栏（系统自带）
   - ✅ 标题栏 logo + "Blur Arc" → Task 1
   - ✅ 相册 Tab 工具栏 → Task 2
   - ✅ 上传 Tab → Task 3
   - ✅ 设置 Tab → Task 4
   - ✅ 底部导航 → 不变
   - ✅ 连接页 2 步流程 → Task 5 + 6
   - ✅ 日历/预览/文件夹 → 不变

2. **占位符扫描** — 无 "TBD"、"TODO"、占位实现

3. **类型一致性** — 所有 Widget 返回类型保持一致（Scaffold/Widget），HomePage 的 `_pages` 列表保持不变
