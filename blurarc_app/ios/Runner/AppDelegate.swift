import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  // 通道名必须与 android/app/src/main/kotlin/.../MainActivity.kt、
  // lib/services/device_info_service.dart 三方保持一致
  private let deviceInfoChannelName = "blurarc/device_info"
  private let getDeviceInfoMethod = "getDeviceInfo"

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)

    let channel = FlutterMethodChannel(
      name: deviceInfoChannelName,
      // FlutterImplicitEngineBridge 没有 binaryMessenger 属性，
      // 必须通过 applicationRegistrar.messenger() 获取
      binaryMessenger: engineBridge.applicationRegistrar.messenger()
    )
    channel.setMethodCallHandler { (call, result) in
      // UIDevice 访问要求在主线程；handler 默认在主线程执行，但显式包装以防 SDK 行为变化
      DispatchQueue.main.async {
        switch call.method {
        case self.getDeviceInfoMethod:
          result(["name": UIDevice.current.name])
        default:
          result(FlutterMethodNotImplemented)
        }
      }
    }
  }
}
