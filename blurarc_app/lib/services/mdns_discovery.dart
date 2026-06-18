/// mDNS 服务发现 — 扫描局域网内的 Blur Arc 服务
///
/// 注意：当前为占位实现，实际使用请参考 multicast_dns 包的最新 API
library;

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

/// mDNS 发现服务（占位实现）
class MdnsDiscovery {
  /// 扫描局域网内的 Blur Arc 服务
  /// 当前直接返回空流，请手动输入 IP/端口连接
  Stream<DiscoveredService> discover({
    Duration timeout = const Duration(seconds: 5),
  }) async* {
    // TODO: 参考 multicast_dns 包的最新 API 实现 mDNS 发现
    // 参考：https://pub.dev/packages/multicast_dns
  }

  /// 释放资源
  void dispose() {}
}
