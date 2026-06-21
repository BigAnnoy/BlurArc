# 移动端 4 个 Bug 排查报告

> 日期：2026-06-20
> 来源：模拟器联调测试反馈

---

## Bug 1：地址/端口输错时无友好提示

### 现象
手动输入 IP 和端口时，如果端口输错（如 8900 写成 8901），App 显示的是原始 Dio 异常信息，而非用户友好的"未找到设备"提示。

### 根因
`blurarc_app/lib/screens/connect_screen.dart` 第 103-105 行：

```dart
} catch (e) {
  setState(() => _statusMessage = '配对请求失败: $e');
}
```

`e` 是 `DioException`，toString() 输出一大串英文堆栈信息。用户根本看不懂。

### 修复方案
在 catch 中区分错误类型：
- 连接超时 / 连接被拒绝 → "未找到设备，请检查地址和端口"
- 其他错误 → 显示简化错误信息

```dart
} catch (e) {
  final msg = e.toString().toLowerCase();
  String display;
  if (msg.contains('socket') || msg.contains('connection') ||
      msg.contains('timeout') || msg.contains('refused')) {
    display = '未找到设备，请检查地址和端口';
  } else {
    display = '连接失败，请重试';
  }
  setState(() => _statusMessage = display);
}
```

---

## Bug 2：配对码输入框溢出 + 退格键无效

### 现象
1. 输入字母时可能超出输入框边界
2. 输错后按输入法删除键没反应，无法回退到上一个输入框

### 根因
`blurarc_app/lib/screens/pairing_code_screen.dart` 第 229-262 行：

**问题 A — 溢出：**
6 个输入框各 48px 宽 + 左右各 4px margin = 6×56 = 336px。加上 24px 屏幕边距，总需 384px。小屏手机可能不够。同时 `fontSize: 24` 配合固定宽度容易溢出。

**问题 B — 退格无效：**
```dart
onChanged: (v) {
  if (v.isNotEmpty && i < 5) {
    _focusNodes[i + 1].requestFocus();
  }
  // ❌ 没有处理 v 变空时回退焦点的逻辑
  // ❌ 没有处理空框按退格回退到上一个框的逻辑
},
```

Flutter 的 OTP 输入有两个经典坑：
1. `onChanged` 在内容从 "有" 变 "空" 时会触发（退格清空当前框），但没有写回退逻辑
2. 在 **空框** 上按退格，`onChanged` **不触发**（内容没变），需要用 `KeyboardListener` 或 `RawKeyboardListener` 监听删除键

### 修复方案

1. **缩小输入框**：`width: 40`，`fontSize: 20`，`margin: horizontal: 3`
2. **添加退格回退逻辑**：用 `KeyboardListener` 监听 BackspaceKey
3. **添加 keyboardType**：`TextInputType.text` + `textCapitalization: TextCapitalization.characters`

```dart
// 伪代码
KeyboardListener(
  focusNode: _focusNodes[i],
  onKeyEvent: (event) {
    if (event is KeyDownEvent &&
        event.logicalKey == LogicalKeyboardKey.backspace &&
        _codeControllers[i].text.isEmpty &&
        i > 0) {
      _focusNodes[i - 1].requestFocus();
      _codeControllers[i - 1].clear();
    }
  },
  child: TextField(...),
)
```

---

## Bug 3：手机端无法预览照片（缩略图和预览图都加载失败）

### 现象
相册网格中的缩略图和点击后的全屏预览都无法加载，显示错误图标。

### 根因
**`Image.network` 和 `CachedNetworkImage` 不发送 Authorization 头！**

后端的三个图片端点全部要求 Bearer token 认证：

| 端点 | 认证检查 | 行号 |
|------|----------|------|
| `/api/mobile/thumbnail` | ✅ 需要 token | 624-626 |
| `/api/mobile/preview` | ✅ 需要 token | 688-690 |
| `/api/mobile/file` | ✅ 需要 token | 659-661 |

而前端代码：

```dart
// album_screen.dart 第 432 行 — 缩略图
Image.network(
  api.getThumbnailUrl(photo.path),  // ❌ 纯 URL，无 auth header
  ...
),

// photo_preview_screen.dart 第 115-116 行 — 预览图
CachedNetworkImage(
  imageUrl: widget.api.getPreviewUrl(p.path),  // ❌ 纯 URL，无 auth header
  ...
),
```

`ApiClient` 的 Dio 实例有拦截器自动加 Authorization 头，但 `Image.network` 和 `CachedNetworkImage` 用的是自己的 HTTP 客户端，不走 Dio。所以所有图片请求都返回 401。

### 修复方案

**方案 A（推荐）：** 在 URL 中附加 token query 参数，后端同时支持 query 参数取 token。

前端：
```dart
String getThumbnailUrl(String path) =>
    '$baseUrl/api/mobile/thumbnail?path=${Uri.encodeComponent(path)}'
    '&token=${_token ?? ''}';
```

后端 `_extract_token()` 增加 query fallback：
```python
def _extract_token(self) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    # fallback: query parameter (for Image.network / CachedNetworkImage)
    return request.args.get("token")
```

**方案 B：** 使用 `CachedNetworkImage` 的 `httpHeaders` 参数（但 `Image.network` 需要替换为 `CachedNetworkImage`）。

选择 **方案 A**，因为改动最小，且 `Image.network` 不需要替换。

---

## Bug 4：上传 Tab 提示"未连接到电脑"

### 现象
配对成功进入主页后，切到"上传"Tab，显示"未连接到电脑"。

### 根因
`blurarc_app/lib/screens/home_page.dart` 第 32 行：

```dart
_pages = [
  AlbumScreen(api: widget.api),
  const UploadScreen(),          // ❌ 没有传 api！
  SettingsScreen(api: widget.api),
];
```

`UploadScreen` 的 `api` 参数是可选的（`final ApiClient? api;`），不传时为 null。而 `upload_screen.dart` 第 27 行：

```dart
if (api == null || !api.isConnected) {
  return Center(... '未连接到电脑' ...);
}
```

所以永远显示"未连接到电脑"。

### 修复方案
一行修改：

```dart
_pages = [
  AlbumScreen(api: widget.api),
  UploadScreen(api: widget.api),   // ✅ 传入 api
  SettingsScreen(api: widget.api),
];
```

注意：去掉 `const` 关键字（因为 `widget.api` 不是编译时常量）。

---

## 修复优先级

| 优先级 | Bug | 影响 | 改动量 |
|--------|-----|------|--------|
| P0 | Bug 4：上传 Tab 无 api | 功能完全不可用 | 1 行 |
| P0 | Bug 3：图片预览 401 | 功能完全不可用 | 前后端各改几行 |
| P1 | Bug 2：配对码输入框 | 体验差，但不阻断流程 | ~30 行 |
| P1 | Bug 1：地址错误提示 | 体验差，但不阻断流程 | ~10 行 |
