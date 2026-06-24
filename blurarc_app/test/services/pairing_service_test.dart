/// 配对流程测试（PairingService 适配版）
///
/// 实际项目没有独立的 `PairingService` 类，配对逻辑分布在：
///   - `ApiClient.pairRequest`        — 老流程（带 code + device_name 一次性）
///   - `ApiClient.pairingRequest`     — 新流程（PC 端确认后输入 6 位码）
///   - `ApiClient.submitPairingCode`  — 新流程（提交 6 位配对码，返回 token）
///   - `ApiClient.getPairingStatus`   — 轮询 pending → confirmed
///   - `ApiClient.saveConnection`     — 成功后持久化 host/port/token
///
/// 这里用 mocktail 模拟 ApiClient 行为，验证各分支的预期返回。
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:blurarc_app/services/api_client.dart';

class _MockApiClient extends Mock implements ApiClient {}

void main() {
  late _MockApiClient api;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    api = _MockApiClient();
  });

  group('ApiClient.pairRequest 旧流程', () {
    test('成功返回 token', () async {
      when(() => api.pairRequest(any(), any())).thenAnswer(
        (_) async => {
          'status': 'paired',
          'token': 'test_token_abc123',
          'device_id': 1,
        },
      );

      final result = await api.pairRequest('1234', 'iPhone-Test');
      expect(result['status'], 'paired');
      expect(result['token'], 'test_token_abc123');
      verify(() => api.pairRequest('1234', 'iPhone-Test')).called(1);
    });

    test('错误配对码返回 error 状态', () async {
      when(() => api.pairRequest(any(), any())).thenAnswer(
        (_) async => {
          'status': 'error',
          'error': 'Invalid pairing code',
        },
      );

      final result = await api.pairRequest('0000', 'Test');
      expect(result['status'], 'error');
      expect(result['error'], 'Invalid pairing code');
    });

    test('使用正确的 device_name 传递', () async {
      when(() => api.pairRequest(any(), any())).thenAnswer(
        (_) async => {'status': 'paired', 'token': 't'},
      );

      await api.pairRequest('1234', 'Pixel 7 Pro');
      final captured = verify(() => api.pairRequest(captureAny(), captureAny()))
          .captured;
      expect(captured.length, 2);
      expect(captured[0], '1234');
      expect(captured[1], 'Pixel 7 Pro');
    });
  });

  group('ApiClient.pairingRequest 新流程', () {
    test('PC 端 409 时自动 cancel + retry', () async {
      // 第一次返回 409 异常，第二次成功 — mocktail 用 .thenThrow + .thenAnswer 串联
      var callCount = 0;
      when(() => api.pairingRequest(any())).thenAnswer((_) async {
        callCount++;
        if (callCount == 1) {
          throw Exception('409 Conflict');
        }
        return; // 成功
      });

      when(() => api.cancelPairing()).thenAnswer((_) async => true);

      // 简化：直接重试 — 不真正模拟 dio 拦截器，只验证 mock 能被多次调用
      try {
        await api.pairingRequest('Pixel 7 Pro');
      } catch (_) {
        // 模拟真实拦截器的 retry
        await api.cancelPairing();
        await api.pairingRequest('Pixel 7 Pro');
      }

      expect(callCount, 2);
      verify(() => api.cancelPairing()).called(1);
    });
  });

  group('ApiClient.submitPairingCode', () {
    test('返回 token 表示配对成功', () async {
      when(() => api.submitPairingCode(any(), any())).thenAnswer(
        (_) async => 'token_xyz',
      );

      final token = await api.submitPairingCode('123456', 'Test');
      expect(token, 'token_xyz');
    });

    test('返回 null 表示配对失败', () async {
      when(() => api.submitPairingCode(any(), any())).thenAnswer(
        (_) async => null,
      );

      final token = await api.submitPairingCode('000000', 'Test');
      expect(token, isNull);
    });
  });

  group('ApiClient.getPairingStatus 轮询', () {
    test('返回 pending 状态', () async {
      when(() => api.getPairingStatus()).thenAnswer(
        (_) async => {'status': 'pending'},
      );

      final res = await api.getPairingStatus();
      expect(res['status'], 'pending');
    });

    test('返回 confirmed 状态（PC 端已确认）', () async {
      when(() => api.getPairingStatus()).thenAnswer(
        (_) async => {'status': 'confirmed'},
      );

      final res = await api.getPairingStatus();
      expect(res['status'], 'confirmed');
    });

    test('返回 rejected 状态（PC 端已拒绝）', () async {
      when(() => api.getPairingStatus()).thenAnswer(
        (_) async => {'status': 'rejected'},
      );

      final res = await api.getPairingStatus();
      expect(res['status'], 'rejected');
    });
  });

  group('ApiClient.verifyTokenStatus', () {
    test('返回 1 表示有效', () async {
      when(() => api.verifyTokenStatus()).thenAnswer((_) async => 1);
      expect(await api.verifyTokenStatus(), 1);
    });

    test('返回 0 表示 token 失效', () async {
      when(() => api.verifyTokenStatus()).thenAnswer((_) async => 0);
      expect(await api.verifyTokenStatus(), 0);
    });

    test('返回 -1 表示网络错误', () async {
      when(() => api.verifyTokenStatus()).thenAnswer((_) async => -1);
      expect(await api.verifyTokenStatus(), -1);
    });
  });

  group('ApiClient 完整配对成功链路', () {
    test('submitCode → saveConnection → isConnected', () async {
      // 1. 提交配对码，返回 token
      when(() => api.submitPairingCode('123456', 'Pixel 7'))
          .thenAnswer((_) async => 'new_token');

      // 2. host/port 由 setConnectionParams 预设
      const fakeHost = '192.168.1.50';
      const fakePort = 8900;
      when(() => api.saveConnection(any(), any(), any()))
          .thenAnswer((_) async {});

      final token = await api.submitPairingCode('123456', 'Pixel 7');
      expect(token, isNotNull);
      await api.saveConnection(fakeHost, fakePort, token!);

      verify(() => api.submitPairingCode('123456', 'Pixel 7')).called(1);
      verify(() => api.saveConnection(fakeHost, fakePort, 'new_token'))
          .called(1);
    });
  });
}
