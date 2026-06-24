import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:blurarc_app/services/api_client.dart';

void main() {
  group('ApiClient 连接状态', () {
    test('isConnected 初始为 false', () {
      final api = ApiClient();
      expect(api.isConnected, isFalse);
    });

    test('setConnectionParams 后 host/port 被设置', () {
      final api = ApiClient();
      api.setConnectionParams('192.168.1.100', 8900);
      expect(api.host, '192.168.1.100');
      expect(api.port, 8900);
    });

    test('baseUrl 正确拼接', () {
      final api = ApiClient();
      api.setConnectionParams('192.168.1.100', 8900);
      expect(api.baseUrl, 'http://192.168.1.100:8900');
    });

    test('设置 host 后 isConnected 仍为 false（缺 token）', () {
      final api = ApiClient();
      api.setConnectionParams('192.168.1.100', 8900);
      expect(api.isConnected, isFalse);
    });
  });

  group('ApiClient URL 生成', () {
    test('thumbnail URL 包含 host/port/path/token', () {
      final api = ApiClient();
      api.setConnectionParams('192.168.1.100', 8900);
      final url = api.getThumbnailUrl('/photos/2024/test.jpg');
      expect(url, contains('192.168.1.100:8900'));
      expect(url, contains('thumbnail'));
      expect(url, contains('path='));
      expect(url, contains('token='));
      // path 应被 URL 编码
      expect(url, contains(Uri.encodeComponent('/photos/2024/test.jpg')));
    });

    test('file URL 包含 file 端点', () {
      final api = ApiClient();
      api.setConnectionParams('10.0.0.5', 8900);
      final url = api.getFileUrl('/a/b.jpg');
      expect(url, contains('10.0.0.5:8900'));
      expect(url, contains('file'));
    });

    test('preview URL 包含 preview 端点', () {
      final api = ApiClient();
      api.setConnectionParams('10.0.0.5', 8900);
      final url = api.getPreviewUrl('/a/b.jpg');
      expect(url, contains('preview'));
    });
  });

  group('ApiClient SharedPreferences 持久化', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('saveConnection 后能从 storage 读出', () async {
      final api = ApiClient();
      await api.saveConnection('192.168.1.10', 8900, 'token_xyz');
      expect(api.host, '192.168.1.10');
      expect(api.port, 8900);
      expect(api.token, 'token_xyz');
      expect(api.isConnected, isTrue);

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('mobile_host'), '192.168.1.10');
      expect(prefs.getInt('mobile_port'), 8900);
      expect(prefs.getString('mobile_token'), 'token_xyz');
    });

    test('loadFromStorage 之前没有数据时返回 false', () async {
      final api = ApiClient();
      final ok = await api.loadFromStorage();
      expect(ok, isFalse);
      expect(api.host, isNull);
      expect(api.port, isNull);
      expect(api.token, isNull);
    });

    test('loadFromStorage 读取已有数据并恢复 isConnected', () async {
      SharedPreferences.setMockInitialValues({
        'mobile_host': '10.0.0.1',
        'mobile_port': 9000,
        'mobile_token': 'saved_token',
      });
      final api = ApiClient();
      final ok = await api.loadFromStorage();
      expect(ok, isTrue);
      expect(api.host, '10.0.0.1');
      expect(api.port, 9000);
      expect(api.token, 'saved_token');
      expect(api.isConnected, isTrue);
    });

    test('disconnect 后 storage 被清空', () async {
      SharedPreferences.setMockInitialValues({
        'mobile_host': '10.0.0.1',
        'mobile_port': 9000,
        'mobile_token': 'old',
      });
      final api = ApiClient();
      await api.loadFromStorage();
      await api.disconnect();
      expect(api.isConnected, isFalse);
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('mobile_host'), isNull);
      expect(prefs.getInt('mobile_port'), isNull);
      expect(prefs.getString('mobile_token'), isNull);
    });
  });

  group('ApiClient onDisconnected 回调', () {
    test('回调能被赋值并调用', () async {
      final api = ApiClient();
      var called = 0;
      api.onDisconnected = () => called++;
      // 直接调用回调（仅验证赋值可工作）
      api.onDisconnected?.call();
      expect(called, 1);
    });
  });

  // ===== 用 mocktail 验证 mock 用法 =====
  //
  // 由于 ApiClient 在内部构造 Dio，无法注入 mock，这里我们用 mocktail
  // 验证：在其他测试中（widget 测试），我们可以 mock 整个 ApiClient。
  // 本组用最简调用验证 mocktail 集成正确。
  group('mocktail 集成验证', () {
    test('MockApiClient 能实例化（不调用 stub）', () {
      final mock = MockApiClient();
      // 构造后 mock 应可用，不抛错
      expect(mock, isA<ApiClient>());
      verifyZeroInteractions(mock);
    });
  });
}

/// 用于 widget / page 测试的 ApiClient mock
class MockApiClient extends Mock implements ApiClient {}
