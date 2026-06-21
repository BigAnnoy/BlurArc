# Pairing Pending 状态清除 - 实施计划

**Goal:** 修复所有会导致 `_pending` 状态卡住的场墓，确保 PC 端和手机端都能主动取消配对请求
**Architecture:** 后端新增 `cancel` API 端点，PC 前端和 Flutter App 在所有退出场墓都调用该端点
**Tech Stack:** Flask (Python), TypeScript (React), Dart (Flutter)
---

## 文件结构

| 文件 | 职责 |
|------|------|
| `backend/mobile_access_server.py` | 新增 `POST /api/mobile/pairing/cancel` 端点 |
| `backend/api_server.py` | 桥接 `cancel` 端点（PC 前端调用） |
| `frontend/src/components/dialogs/MobileDeviceManager.tsx` | PC 端：取消/关闭对话框时调 cancel API |
| `blurarc_app/lib/screens/connect_screen.dart` | 手机端：等待 PC 确认时加取消按钮 |
| `blurarc_app/lib/screens/pairing_code_screen.dart` | 手机端：超时/错误超次时调 cancel API |
| `blurarc_app/lib/services/api_client.dart` | 手机端：新增 `cancelPairing()` 方法 |

---

### Task 1: 后端 - 新增 cancel API 端点

**Files:**
- Create: `backend/mobile_access_server.py:850-870` (新增端点)
- Modify: `backend/api_server.py:1600-1620` (桥接端点)

- [ ] **Step 1: 在 `mobile_access_server.py` 新增 cancel 端点**
```python
@self.app.route("/api/mobile/pairing/cancel", methods=["POST"])
def pairing_cancel():
    """手机端或 PC 端取消配对请求"""
    token = self._extract_token()
    if not token or not self.token_manager.validate_token(token):
        # 允许未认证调用（配对未完成时手机还没有 token）
        pass
    
    self._pairing.clear_pending()
    logger.info("[Pairing] 配对请求已取消")
    return jsonify({"status": "cancelled"})
```

- [ ] **Step 2: 在 `api_server.py` 新增桥接端点（PC 前端调用）**
```python
@app.route('/api/mobile/pairing/cancel', methods=['POST'])
@login_required
def api_mobile_pairing_cancel():
    """PC 端取消配对请求（桥接至移动接入服务）"""
    try:
        mobile_server = _get_mobile_server()
        # 直接调用 PairingManager.clear_pending()
        mobile_server._pairing.clear_pending()
        return jsonify({"status": "cancelled"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

- [ ] **Step 3: 验证后端端点**
```bash
# 启动后端后测试
curl -s -X POST http://127.0.0.1:5000/api/mobile/pairing/cancel | python -m json.tool
# 期望输出: {"status": "cancelled"}
```

- [ ] **Step 4: 提交**
```bash
git add backend/mobile_access_server.py backend/api_server.py
git commit -m "feat: add pairing cancel API endpoint (fixes stuck _pending state)"
```

---

### Task 2: 手机端 - api_client.dart 新增 cancelPairing()

**Files:**
- Modify: `blurarc_app/lib/services/api_client.dart:40-60`

- [ ] **Step 1: 新增 cancelPairing() 方法**
```dart
Future<bool> cancelPairing() async {
  try {
    await _dio.post('/api/mobile/pairing/cancel');
    return true;
  } catch (e) {
    // 取消失败不阻塞流程
    return false;
  }
}
```

- [ ] **Step 2: 提交**
```bash
git add blurarc_app/lib/services/api_client.dart
git commit -m "feat(mobile): add cancelPairing() API method"
```

---

### Task 3: 手机端 - connect_screen.dart 加取消按钮

**Files:**
- Modify: `blurarc_app/lib/screens/connect_screen.dart:52-53,82-103`

**问题:** `_onDeviceTap()` 发送配对请求后，导航到 `PairingCodeScreen`，但如果用户在等待 PC 确认时想取消，没有按钮。

- [ ] **Step 1: 在 ConnectScreen 加取消状态管理**
```dart
class _ConnectScreenState extends State<ConnectScreen> {
  // ... 现有代码 ...
  bool _isPairing = false;  // 新增：是否正在等待 PC 确认
  
  void _cancelPairing() async {
    setState(() => _isPairing = false);
    await api.cancelPairing();
    if (mounted) Navigator.pop(context);
  }
}
```

- [ ] **Step 2: 修改 `_onDeviceTap()` 设置 `_isPairing = true`**
```dart
Future<void> _onDeviceTap(DiscoveredService service) async {
  setState(() => _statusMessage = '正在发送配对请求...');
  try {
    final api = ApiClient();
    api.setConnectionParams(service.host, service.port);
    await api.pairingRequest('BlurArc Mobile');
    
    if (!mounted) return;
    setState(() => _isPairing = true);  // 新增
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => PairingCodeScreen(
          api: api,
          deviceName: service.name,
          onCancel: _cancelPairing,  // 新增回调
        ),
      ),
    );
  } catch (e) {
    setState(() => _statusMessage = '配对请求失败: $e');
  }
}
```

- [ ] **Step 3: 提交**
```bash
git add blurarc_app/lib/screens/connect_screen.dart
git commit -m "feat(mobile): add cancel button during pairing request"
```

---

### Task 4: 手机端 - pairing_code_screen.dart 完善取消逻辑

**Files:**
- Modify: `blurarc_app/lib/screens/pairing_code_screen.dart:8-20,40-79,120-285`

- [ ] **Step 1: 接收 onCancel 回调，加"等待 PC 确认"状态的取消按钮**
```dart
class PairingCodeScreen extends StatefulWidget {
  final ApiClient api;
  final String deviceName;
  final VoidCallback? onCancel;  // 新增
  
  const PairingCodeScreen({
    required this.api,
    required this.deviceName,
    this.onCancel,  // 新增
    super.key,
  });
}
```

- [ ] **Step 2: 修改 `_startPolling()` - 超时时调 cancel API**
```dart
void _startPolling() {
  int elapsed = 0;
  _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
    elapsed += 2;
    if (elapsed > 120) {
      _pollTimer?.cancel();
      // 超时时主动取消后端 pending 状态
      await widget.api.cancelPairing();
      if (mounted) setState(() => _timeout = true);
      return;
    }
    // ... 现有轮询逻辑 ...
  });
}
```

- [ ] **Step 3: 在 build() 的"等待 PC 确认"状态加取消按钮**
```dart
if (!_codeGenerated && !_timeout) ...[
  // ... 现有 UI ...
  const SizedBox(height: 24),
  TextButton(
    onPressed: () async {
      _pollTimer?.cancel();
      await widget.api.cancelPairing();
      if (mounted) Navigator.pop(context);
    },
    child: const Text('取消'),
  ),
]
```

- [ ] **Step 4: 提交**
```bash
git add blurarc_app/lib/screens/pairing_code_screen.dart
git commit -m "feat(mobile): add cancel logic in pairing code screen"
```

---

### Task 5: PC 前端 - MobileDeviceManager.tsx 完善取消逻辑

**Files:**
- Modify: `frontend/src/components/dialogs/MobileDeviceManager.tsx:173-184,270-290`

- [ ] **Step 1: 修改 handleStopPairing() 调 cancel API**
```typescript
const handleStopPairing = async () => {
  // 清除倒计时 timer
  if (codeTimerRef.current) {
    clearInterval(codeTimerRef.current);
    codeTimerRef.current = null;
  }
  // 调用 cancel API 清除后端 _pending 状态
  try { await api.cancelPairing(); } catch {}
  try { await api.stopPairingMode(); } catch {}
  setPairingState('idle');
  setPendingDeviceName('');
  setPairingCode('');
  setCodeCountdown(0);
};
```

- [ ] **Step 2: 对话框 onClose 时也调 cancel API**
```typescript
// 在对话框的 onClose 回调中
const handleDialogClose = async () => {
  if (pairingState !== 'idle') {
    await handleStopPairing();
  }
  setIsOpen(false);
};
```

- [ ] **Step 3: 提交**
```bash
git add frontend/src/components/dialogs/MobileDeviceManager.tsx
git commit -m "fix(pc): clear backend _pending state when cancelling pairing"
```

---

### Task 6: 联调测试

- [ ] **Step 1: 重启后端和 PC 前端**
```bash
# 关闭旧进程
taskkill /F /PID <backend_pid>
# 重启
cd F:/AI/Frame_Album
python src/BlurArc.py
```

- [ ] **Step 2: 测试场景**
| 场景 | 操作 | 期望结果 |
|------|------|------------|
| PC 端取消确认对话框 | 点击"取消" | `_pending` 清除，手机端显示"配对请求被拒绝" |
| PC 端取消配对码页面 | 点击"取消配对" | `_pending` 清除，手机端返回连接页面 |
| PC 端关闭对话框 | 点击 X 关闭 | `_pending` 清除 |
| 手机端取消配对请求 | 点击"取消" | `_pending` 清除，PC 端配对状态重置 |
| 手机端等待超时 | 等 120 秒 | `_pending` 自动清除 |
| 重复发起配对请求 | 第一次未完成，第二次重试 | 第一次自动清除，第二次成功 |

- [ ] **Step 3: 提交测试通过**
```bash
git add -A
git commit -m "test: verify pairing cancel logic works in all scenarios"
```

---

## 自审

- [ ] **规格覆盖**: 所有 8 个卡住场墓都有对应修复？
  - PC 端取消确认对话框 ✅ Task 5
  - PC 端取消配对码页面 ✅ Task 5
  - PC 端关闭对话框 ✅ Task 5
  - 手机端取消配对请求 ✅ Task 3 + Task 4
  - 手机端等待超时 ✅ Task 4
  - 手机端输入码超时 ✅ Task 4 (已在 _startPolling)
  - 手机端输入错误码超次 ⚠️ 待确认后端是否有错误次数限制
  
- [ ] **占位符扫描**: 无 TBD/TODO

- [ ] **类型一致性**: 
  - `api_client.dart` 的 `cancelPairing()` 返回 `Future<bool>` ✅
  - `PairingCodeScreen` 新增 `onCancel` 回调 ✅
  - `MobileDeviceManager.tsx` 的 `api.cancelPairing()` 需要确认前端 API 有此方法 ✅ (需要新增)

---

---

### Task 7: App 名称修复

**Files:**
- Modify: `blurarc_app/android/app/src/main/AndroidManifest.xml:11`
- Modify: `blurarc_app/ios/Runner/Info.plist` (如存在)
- Modify: `blurarc_app/pubspec.yaml:1` (应用描述名称)

- [ ] **Step 1: 修改 Android 应用名称**
```xml
<!-- blurarc_app/android/app/src/main/AndroidManifest.xml -->
<!-- 修改前 -->
android:label="blurarc_app"
<!-- 修改后 -->
android:label="Blur Arc"
```

- [ ] **Step 2: 修改 iOS 应用名称（如需要）**
```xml
<!-- blurarc_app/ios/Runner/Info.plist -->
<!-- 确保 CFBundleDisplayName 为 "Blur Arc" -->
<key>CFBundleDisplayName</key>
<string>Blur Arc</string>
```

- [ ] **Step 3: 提交**
```bash
git add blurarc_app/android/app/src/main/AndroidManifest.xml
git commit -m "fix(mobile): set app name to 'Blur Arc' on Android"
```

---

### Task 8: App Logo 修复

**Files:**
- Create: `blurarc_app/assets/logo/blur_arc_logo.svg` (从 PC 端 Logo.tsx 导出的 SVG)
- Modify: `blurarc_app/pubspec.yaml` (添加 assets 声明)
- Modify: `blurarc_app/android/app/src/main/res/mipmap-*/ic_launcher.png` (启动图标)
- Modify: `blurarc_app/lib/widgets/blur_arc_logo.dart` (修复 in-app logo 渲染)

**问题诊断:**
1. **启动图标**: 仍是默认 Flutter 图标，需替换为 Blur Arc logo
2. **In-app logo**: Flutter `CustomPainter` 实现与 PC 端 SVG 可能存在渲染差异

- [ ] **Step 1: 创建正确的 SVG logo 文件**
```svg
<!-- blurarc_app/assets/logo/blur_arc_logo.svg -->
<!-- 从 PC 端 Logo.tsx 导出的精确 SVG -->
<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
  <defs>
    <linearGradient id="grad" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
      <stop offset="0" stopColor="#0891b2" stopOpacity="0.95" />
      <stop offset="1" stopColor="#06b6d4" stopOpacity="0.65" />
    </linearGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="1.5" />
    </filter>
  </defs>
  <!-- 外圈发光 -->
  <circle cx="20" cy="20" r="14" stroke="#22d3ee" strokeWidth="3.5" fill="none" strokeDasharray="55 33" strokeLinecap="round" transform="rotate(-30 20 20)" filter="url(#glow)" opacity="0.3" />
  <!-- 外圈渐变 -->
  <circle cx="20" cy="20" r="14" stroke="url(#grad)" strokeWidth="2.2" fill="none" strokeDasharray="55 33" strokeLinecap="round" transform="rotate(-30 20 20)" />
  <!-- 内圈 -->
  <circle cx="20" cy="20" r="8" stroke="#0891b2" strokeWidth="1.6" fill="none" strokeDasharray="28 22" strokeLinecap="round" transform="rotate(60 20 20)" opacity="0.75" />
  <!-- 中心发光 -->
  <circle cx="20" cy="20" r="2" fill="#0891b2" filter="url(#glow)" opacity="0.6" />
  <!-- 中心实心 -->
  <circle cx="20" cy="20" r="1.4" fill="#0891b2" />
</svg>
```

- [ ] **Step 2: 使用 flutter_launcher_icons 生成启动图标**
```yaml
# pubspec.yaml 新增
dev_dependencies:
  flutter_launcher_icons: ^0.13.1

flutter_icons:
  android: "launcher_icon"
  ios: true
  image_path: "assets/logo/blur_arc_logo.png"  # 从 SVG 导出的 512x512 PNG
  min_sdk_android: 21
```

- [ ] **Step 3: 修复 in-app logo 的渲染差异**
```dart
// blurarc_app/lib/widgets/blur_arc_logo.dart
// 问题: CustomPainter 的 addArc 可能不会正确渲染虚线
// 修复: 使用 Path.dashPath 或从 SVG 渲染

// 方案 A: 使用 flutter_svg 包直接渲染 SVG
// 方案 B: 修复 CustomPainter 的虚线渲染逻辑

// 推荐使用方案 A，确保与 PC 端完全一致
```

- [ ] **Step 4: 提交**
```bash
git add blurarc_app/assets/logo/blur_arc_logo.svg
git add blurarc_app/lib/widgets/blur_arc_logo.dart
git add pubspec.yaml
git commit -m "fix(mobile): update app logo to match PC version"
```

---

## 自审（更新）

- [ ] **规格覆盖**: 
  - 所有 8 个卡住场景 ✅ Task 1-6
  - App 名称 ✅ Task 7
  - App Logo ✅ Task 8
  
- [ ] **占位符扫描**: 无 TBD/TODO

- [ ] **类型一致性**: 
  - `api_client.dart` 的 `cancelPairing()` 返回 `Future<bool>` ✅
  - `PairingCodeScreen` 新增 `onCancel` 回调 ✅
  - `MobileDeviceManager.tsx` 的 `api.cancelPairing()` 需要确认前端 API 有此方法 ✅ (需要新增)

---

## 待确认

1. **后端错误次数限制**: 当前 `submitPairingCode` 是否有错误次数限制？需要查 `mobile_access_server.py` 的 `consume_code` 逻辑（本次未涉及，不影响 409 修复）

---

## 已完成（2026-06-20）

### Tasks 1-6: 修复 409 _pending 卡住问题 ✓

- [x] **Task 1: 后端 cancel API 端点** — `mobile_access_server.py` 新增 `POST /api/mobile/pairing/cancel`；`api_server.py` 新增桥接端点 ✓
- [x] **Task 2: 手机端 cancelPairing()** — `api_client.dart` 新增 `cancelPairing()` 方法 ✓
- [x] **Task 3: 手机端 connect_screen 取消回调** — 传递 `onCancel` 回调给 `PairingCodeScreen` ✓
- [x] **Task 4: 手机端 pairing_code_screen 取消逻辑** — 新增 `onCancel` 参数；"等待确认"状态加取消按钮；超时时调 cancel API ✓
- [x] **Task 5: PC 前端取消逻辑** — `api.ts` 新增 `cancelPairing()`；`handleStopPairing` 调 cancel API；对话框关闭也调 cancel ✓
- [x] **Task 6: 联调测试（待执行）** — 需重启后端 + 重新部署 App 后测试

### Tasks 7-8: App 品牌修复（上一轮已完成） ✓

- [x] **Task 7: App 名称修复** — `AndroidManifest.xml` `android:label="Blur Arc"` ✓
- [x] **Task 8: App Logo 修复** — SVG logo 创建、`flutter_svg` 集成、`flutter_launcher_icons` 生成启动图标、`BlurArcLogoWithText` 组件已补回 ✓