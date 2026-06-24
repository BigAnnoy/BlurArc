/// PairingCodeScreen widget 测试
///
/// 实际项目使用 `pairing_code_screen.dart`（不是 `pairing_page.dart`）。
/// 屏幕本身需要 `ApiClient`（不带 provider），所以直接构造。
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:blurarc_app/screens/pairing_code_screen.dart';
import 'package:blurarc_app/services/api_client.dart';

class _MockApiClient extends Mock implements ApiClient {}

Widget _buildScreen(_MockApiClient api) {
  return MaterialApp(
    home: PairingCodeScreen(
      api: api,
      deviceName: 'TestDevice',
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late _MockApiClient api;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    api = _MockApiClient();

    // 默认：pairing status 永远 pending（避免 timer 触发 setState 抛错）
    when(() => api.getPairingStatus()).thenAnswer(
      (_) async => {'status': 'pending'},
    );
    when(() => api.cancelPairing()).thenAnswer((_) async => true);
  });

  testWidgets('初始显示「配对请求已发送」等待界面', (tester) async {
    await tester.pumpWidget(_buildScreen(api));
    await tester.pump();

    expect(find.text('配对请求已发送'), findsOneWidget);
    expect(find.text('请在电脑端确认配对'), findsOneWidget);
    expect(find.text('等待电脑确认...'), findsOneWidget);
  });

  testWidgets('显示「取消」按钮可点击', (tester) async {
    await tester.pumpWidget(_buildScreen(api));
    await tester.pump();

    final cancelBtn = find.text('取消');
    expect(cancelBtn, findsOneWidget);
    // 取消按钮可点击（在等待界面）
    final widget = tester.widget<TextButton>(
      find.ancestor(of: cancelBtn, matching: find.byType(TextButton)),
    );
    expect(widget.onPressed, isNotNull);
  });

  testWidgets('PC 端确认后切换到「输入配对码」界面', (tester) async {
    // 第一次 poll 返回 confirmed — 触发 _codeGenerated 状态
    var called = 0;
    when(() => api.getPairingStatus()).thenAnswer((_) async {
      called++;
      return {'status': called == 1 ? 'confirmed' : 'pending'};
    });

    await tester.pumpWidget(_buildScreen(api));
    // 让 timer 跑一轮
    await tester.pump(const Duration(seconds: 2));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // 应切换到「输入配对码」状态
    expect(find.text('步骤 2/2：输入配对码'), findsOneWidget);
    expect(find.text('在电脑端查看配对码并输入'), findsOneWidget);
  });

  testWidgets('PC 端拒绝时显示「配对请求被拒绝」', (tester) async {
    var called = 0;
    when(() => api.getPairingStatus()).thenAnswer((_) async {
      called++;
      return {'status': called == 1 ? 'rejected' : 'pending'};
    });

    await tester.pumpWidget(_buildScreen(api));
    await tester.pump(const Duration(seconds: 2));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('配对请求被拒绝'), findsOneWidget);
    expect(find.text('电脑端拒绝了配对请求，请重试'), findsOneWidget);
  });

  testWidgets('输入配对码后 6 个 TextField 都能输入', (tester) async {
    // 先让屏幕进入 code 输入模式
    when(() => api.getPairingStatus()).thenAnswer(
      (_) async => {'status': 'confirmed'},
    );

    await tester.pumpWidget(_buildScreen(api));
    await tester.pump(const Duration(seconds: 2));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // 应有 6 个 TextField（每个码一位）
    expect(find.byType(TextField), findsNWidgets(6));
  });

  testWidgets('未输入 6 位时「确认配对」按钮禁用', (tester) async {
    when(() => api.getPairingStatus()).thenAnswer(
      (_) async => {'status': 'confirmed'},
    );

    await tester.pumpWidget(_buildScreen(api));
    await tester.pump(const Duration(seconds: 2));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    final confirmBtn = find.widgetWithText(FilledButton, '确认配对');
    expect(confirmBtn, findsOneWidget);
    final btn = tester.widget<FilledButton>(confirmBtn);
    expect(btn.onPressed, isNull); // 0 位时应禁用
  });

  testWidgets('输入 6 位后「确认配对」按钮可点击并调用 submitPairingCode',
      (tester) async {
    when(() => api.getPairingStatus()).thenAnswer(
      (_) async => {'status': 'confirmed'},
    );
    when(() => api.submitPairingCode(any(), any())).thenAnswer(
      (_) async => 'test_token_xyz',
    );
    when(() => api.saveConnection(any(), any(), any())).thenAnswer(
      (_) async {},
    );

    await tester.pumpWidget(_buildScreen(api));
    await tester.pump(const Duration(seconds: 2));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // 找到 6 个 TextField 并逐个输入
    final fields = find.byType(TextField);
    for (var i = 0; i < 6; i++) {
      await tester.enterText(fields.at(i), i.toString());
      await tester.pump();
    }

    // 第 6 位输入完自动调用 submitPairingCode
    await tester.pumpAndSettle(const Duration(milliseconds: 500));
    verify(() => api.submitPairingCode(any(), any())).called(greaterThan(0));
  });

  testWidgets('dispose 时取消 timer（不会调用已 dispose 的 setState）',
      (tester) async {
    await tester.pumpWidget(_buildScreen(api));
    // 替换为另一个 widget 触发 dispose
    await tester.pumpWidget(const MaterialApp(home: Scaffold()));
    // 再等几个 timer tick — 不应抛 "setState after dispose"
    await tester.pump(const Duration(seconds: 3));
    expect(tester.takeException(), isNull);
  });
}
