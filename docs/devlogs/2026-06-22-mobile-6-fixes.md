# 2026-06-22 — 移动端 6 项 UI/交互修复

## 背景
用户反馈移动端 6 个问题，逐项修复。

## 改动汇总

### 1. 上传页 image_picker 双弹问题
**文件：** [upload_screen.dart](../../blurarc_app/lib/screens/upload_screen.dart)

`_pickFiles()` 中原本先调 `pickMultiImage()` 再调 `pickVideo()`，
两个调用各拉起一次系统选择器，用户感知为"选完一次再弹一次"。

`pickMultiImage()` 在 Android 上可以同时选图和视频，单独调一次即可。
删除 `pickVideo` 块。

```dart
// 修改后：只拉起一次系统选择器
final images = await _picker.pickMultiImage();
pickedFiles.addAll(images);
```

### 2. 连接时显示真实设备名
**文件：**
- 新增 [device_info_service.dart](../../blurarc_app/lib/services/device_info_service.dart)
- [connect_screen.dart](../../blurarc_app/lib/screens/connect_screen.dart)
- [settings_screen.dart](../../blurarc_app/lib/screens/settings_screen.dart)
- [pubspec.yaml](../../blurarc_app/pubspec.yaml)

之前 `service.name` 是 mDNS 服务名（`BlurArc._blurarc._tcp.local.`），
显示给用户毫无意义。改用 `device_info_plus` 读取真实设备名：

| 平台 | 设备名来源 |
|------|------------|
| Android | `<manufacturer> <model>`，如 "Pixel 7 Pro" |
| iOS | `iosInfo.name`（用户在系统设置中给设备的命名） |

- `connect_screen.dart`：连接时把 `deviceName` 一并传给 `PairingCodeScreen`
- `settings_screen.dart`：将 "设备信息" 卡片里的 "我的手机" 硬编码改为异步获取

### 3. 设置页隐藏 Token
**文件：** [settings_screen.dart](../../blurarc_app/lib/screens/settings_screen.dart)

移除 `_SettingsItem(label: 'Token', ...)` 卡片项及辅助方法 `_truncateToken()`。
Token 对用户没有意义，且会泄露服务端凭据。

### 4. 相册页双指缩放改每页照片数
**文件：** [album_screen.dart](../../blurarc_app/lib/screens/album_screen.dart)

外层包 `GestureDetector`，监测 `onScaleUpdate` 累积 scale：

| 手势 | scale 变化 | 触发动作 |
|------|------------|----------|
| 双指捏合 | scale < 0.8 | cols -= 1（照片更大） |
| 双指展开 | scale > 1.25 | cols += 1（更多照片） |
| 跨过 25% 阈值 | 一次性触发 | 去抖避免来回抖动 |

| 平台 | 范围 |
|------|------|
| 手机 | 2-4 列（默认 3） |
| 平板 | 3-7 列（默认 5） |

`_cols == 0` 时使用平台默认；超过范围用 `clamp` 限制。

### 5. 移动端高帧率支持
**文件：** [MainActivity.kt](../../blurarc_app/android/app/src/main/kotlin/com/example/blurarc_app/MainActivity.kt)

Android 11 (API 30) + 可以在 Window 上设置 `preferredDisplayModeId` 选最高刷新率。
`onCreate` 中查询 `display.supportedModes` 选 `refreshRate` 最大的 mode，
赋值给 `window.attributes.preferredDisplayModeId`，模拟器和真机自动 90/120Hz。

try-catch 包裹：低版本或不支持的设备（如部分模拟器）会抛异常，静默吞掉保留默认 60Hz。

### 6. 大图查看页加下载原图按钮
**文件：** [photo_preview_screen.dart](../../blurarc_app/lib/screens/photo_preview_screen.dart)

AppBar 增加 `Icons.download_outlined` 按钮：

- 状态机：空闲 → 下载中（带进度环）→ 完成/失败 SnackBar
- URL 来源：`api.getFileUrl(photo.path)`（后端 `/api/mobile/file` 已提供原图）
- 保存目录：`getApplicationDocumentsDirectory()/Downloads/`
  - Android：app-specific external storage，兼容 Android 10+ scoped storage，无需运行时权限
  - iOS：app 沙箱 Documents/Downloads
- 文件名冲突处理：自动加 `(1)`、`(2)` 后缀
- 进度：`Dio.download(onReceiveProgress: ...)` 实时更新 UI

## 验证

```bash
cd blurarc_app
flutter pub get              # +device_info_plus 11.5.0
flutter analyze              # No issues found!
flutter test                 # All tests passed! (5/5)
```

## 相关文件

| 文件 | 说明 |
|------|------|
| `blurarc_app/lib/services/device_info_service.dart` | 新增：跨平台设备名 |
| `blurarc_app/lib/screens/upload_screen.dart` | 修复：双弹 |
| `blurarc_app/lib/screens/connect_screen.dart` | 修复：真实设备名 |
| `blurarc_app/lib/screens/settings_screen.dart` | 修复：隐藏 token + 真实设备名 |
| `blurarc_app/lib/screens/album_screen.dart` | 新增：双指缩放改列数 |
| `blurarc_app/lib/screens/photo_preview_screen.dart` | 新增：下载原图 |
| `blurarc_app/android/app/src/main/kotlin/.../MainActivity.kt` | 新增：高帧率 |
| `blurarc_app/pubspec.yaml` | 新增依赖 device_info_plus ^11.0.0 |
