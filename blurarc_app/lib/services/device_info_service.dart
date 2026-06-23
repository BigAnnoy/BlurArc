import 'dart:io';

import 'package:flutter/services.dart';

/// 获取移动设备的真实名称（用户/系统可读）
/// - Android: 通过 MethodChannel 调用原生 `Build.MANUFACTURER` / `Build.MODEL`
///   输出示例："Pixel 7 Pro" / "Samsung Galaxy S23"
/// - iOS: 通过 MethodChannel 调用原生 `UIDevice.current.name`
///   输出示例：用户在系统中给设备的命名（如 "Tom 的 iPhone"）
/// - 其他 / 通道异常: 回退到 "BlurArc Mobile"
class DeviceInfoService {
  // 通道名必须与 android/app/src/main/kotlin/.../MainActivity.kt、
  // ios/Runner/AppDelegate.swift 三方保持一致
  static const _channel = MethodChannel('blurarc/device_info');

  static Future<String> getDeviceName() async {
    try {
      final info = await _channel.invokeMapMethod<String, dynamic>(
        'getDeviceInfo',
      );
      if (info == null) return 'BlurArc Mobile';

      if (Platform.isAndroid) {
        final mfr = (info['manufacturer'] as String? ?? '').trim();
        final model = (info['model'] as String? ?? '').trim();
        if (mfr.isEmpty || model.toLowerCase().startsWith(mfr.toLowerCase())) {
          return model.isEmpty ? 'BlurArc Mobile' : model;
        }
        return '$mfr $model';
      }
      if (Platform.isIOS) {
        final name = (info['name'] as String? ?? '').trim();
        return name.isEmpty ? 'BlurArc Mobile' : name;
      }
    } catch (_) {
      // 通道未注册（理论上不会发生）或原生抛错 → 回退默认名
    }
    return 'BlurArc Mobile';
  }
}
