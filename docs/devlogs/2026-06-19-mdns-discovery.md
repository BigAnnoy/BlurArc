# 2026-06-19 Flutter mDNS 自动发现实现

## 背景

`mdns_discovery.dart` 原为空壳（TODO 占位），`multicast_dns: ^0.3.2` 依赖已加但未实现。
后端 `ZeroconfPublisher` 广播 `_blurarc._tcp.local.` 服务，但 Flutter 端无法发现。

## 改动

### `blurarc_app/lib/services/mdns_discovery.dart`（重写）

完整实现 PTR → SRV → A 三阶段 mDNS 查询：

1. **PTR 查询**：`ResourceRecordQuery.serverPointer('_blurarc._tcp.local.')` 发现所有服务实例
2. **SRV 查询**：`ResourceRecordQuery.service(instanceName)` 获取主机名 + 端口
3. **A 查询**：`ResourceRecordQuery.addressIPv4(host)` 解析 IP 地址

设计要点：
- 每发现一个服务立即 `yield`（流式返回，UI 实时更新列表）
- A 记录查询失败时降级使用 SRV 中的主机名
- 所有异常静默处理，UI 自动回退到手动输入界面
- `MDnsClient` 生命周期：首次 `discover()` 时 `start()`，`dispose()` 时 `stop()`

### `blurarc_app/android/app/src/main/AndroidManifest.xml`

新增 4 个权限：
- `INTERNET` — 网络通信
- `ACCESS_NETWORK_STATE` — 网络状态检测
- `ACCESS_WIFI_STATE` — Wi-Fi 状态检测
- `CHANGE_WIFI_MULTICAST_STATE` — mDNS 组播接收（真机自动发现必需）

### `blurarc_app/ios/Runner/Info.plist`

新增 iOS 14+ 本地网络权限声明：
- `NSBonjourServices` — `_blurarc._tcp`
- `NSLocalNetworkUsageDescription` — 中文描述

## multicast_dns 0.3.3+1 API 要点

`lookup<T>()` 接受 `ResourceRecordQuery` 对象，不是 `ResourceRecordType` + `String`。
命名构造器：`serverPointer(name)` / `service(name)` / `addressIPv4(name)` / `text(name)`。

## 限制

- Android 模拟器不支持组播（NAT 隔离），mDNS 自动发现只能在真机测试
- 模拟器可通过手动输入 `10.0.2.2:8900` 测试后续配对流程

## 验证

- `flutter analyze`: 0 errors（mdns_discovery.dart 无错误）
