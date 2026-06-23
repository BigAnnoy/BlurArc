package com.example.blurarc_app

import android.os.Build
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    // 通道名必须与 ios/Runner/AppDelegate.swift、lib/services/device_info_service.dart 三方保持一致
    private companion object {
        const val CHANNEL_NAME = "blurarc/device_info"
        const val METHOD_GET_DEVICE_INFO = "getDeviceInfo"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // 启用 90/120Hz 高刷屏：让系统按显示模式选最高刷新率
        // Android 11 (API 30) + 支持在 Window 上设置 preferredFrameRate
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            try {
                val display = display ?: return
                val highest = display.supportedModes
                    .maxByOrNull { it.refreshRate }
                if (highest != null) {
                    window.attributes = window.attributes.also { attrs ->
                        @Suppress("DEPRECATION")
                        attrs.preferredDisplayModeId = highest.modeId
                    }
                }
            } catch (_: Throwable) {
                // 忽略：部分设备 / 模拟器不支持，保留系统默认
            }
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL_NAME)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    METHOD_GET_DEVICE_INFO -> result.success(
                        mapOf(
                            "manufacturer" to Build.MANUFACTURER,
                            "model" to Build.MODEL,
                        )
                    )
                    else -> result.notImplemented()
                }
            }
    }
}
