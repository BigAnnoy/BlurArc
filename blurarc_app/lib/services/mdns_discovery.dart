import 'dart:async';
import 'package:multicast_dns/multicast_dns.dart';

/// 发现的服务信息
class DiscoveredService {
  final String name;
  final String host;
  final int port;

  DiscoveredService({
    required this.name,
    required this.host,
    required this.port,
  });

  @override
  String toString() => '$name @ $host:$port';
}

/// mDNS 发现服务 — 扫描局域网内的 Blur Arc 服务
///
/// 后端通过 ZeroconfPublisher 广播 `_blurarc._tcp.local.` 服务。
/// 此类执行 PTR → SRV → A 三阶段查询，解析出服务实例名、IP 和端口。
class MdnsDiscovery {
  static const String _serviceType = '_blurarc._tcp.local.';

  MDnsClient? _client;
  bool _started = false;

  /// 扫描局域网内的 Blur Arc 服务
  ///
  /// 返回一个流，每发现一个服务就 yield 一个 [DiscoveredService]。
  /// 流在查询超时后自动结束。
  Stream<DiscoveredService> discover({
    Duration timeout = const Duration(seconds: 5),
  }) async* {
    // 启动 mDNS 客户端（权限/网络不可用时静默返回空流）
    try {
      await _ensureStarted();
    } catch (_) {
      return;
    }

    try {
      // 阶段 1: 查询 PTR 记录，发现所有服务实例
      // lookup 返回的流会在内部超时后自动结束
      await for (final ptr in _client!.lookup<PtrResourceRecord>(
        ResourceRecordQuery.serverPointer(_serviceType),
        timeout: timeout,
      )) {
        // 阶段 2+3: 对每个实例查询 SRV (获取端口+主机名) 和 A (获取 IP)
        final service = await _resolveService(ptr.domainName, timeout: timeout);
        if (service != null) {
          yield service;
        }
      }
    } catch (_) {
      // 查询失败，静默处理 — UI 会回退到手动输入
    }
  }

  /// 解析单个服务实例：SRV 记录 → 主机名+端口，A 记录 → IP 地址
  Future<DiscoveredService?> _resolveService(
    String instanceName, {
    Duration timeout = const Duration(seconds: 5),
  }) async {
    String? host;
    int? port;

    // 查询 SRV 记录
    try {
      await for (final srv in _client!.lookup<SrvResourceRecord>(
        ResourceRecordQuery.service(instanceName),
        timeout: timeout,
      )) {
        host = srv.target;
        port = srv.port;
      }
    } catch (_) {
      return null;
    }

    if (host == null || port == null) return null;

    // 查询 A 记录获取 IP 地址
    String? ipAddress;
    try {
      await for (final addr in _client!.lookup<IPAddressResourceRecord>(
        ResourceRecordQuery.addressIPv4(host),
        timeout: timeout,
      )) {
        ipAddress = addr.address.address;
      }
    } catch (_) {
      // A 记录查询失败时降级使用主机名
    }

    return DiscoveredService(
      name: _extractDisplayName(instanceName),
      host: ipAddress ?? host,
      port: port,
    );
  }

  /// 从服务实例名中提取可读名称
  /// 例: "Blur Arc on DESKTOP-ABC._blurarc._tcp.local." → "Blur Arc on DESKTOP-ABC"
  String _extractDisplayName(String instanceName) {
    final idx = instanceName.indexOf('._blurarc');
    if (idx > 0) {
      return instanceName.substring(0, idx);
    }
    return instanceName.replaceAll('._blurarc._tcp.local.', '');
  }

  Future<void> _ensureStarted() async {
    if (!_started) {
      _client = MDnsClient();
      await _client!.start();
      _started = true;
    }
  }

  /// 释放资源
  void dispose() {
    if (_started) {
      _client?.stop();
      _client = null;
      _started = false;
    }
  }
}
