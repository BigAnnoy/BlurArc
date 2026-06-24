/// UploadScreen widget 测试（UploadPage 适配版）
///
/// 实际项目使用 `upload_screen.dart`（不是 `upload_page.dart`）。
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:blurarc_app/screens/upload_screen.dart';
import 'package:blurarc_app/services/api_client.dart';
import 'package:blurarc_app/services/theme_provider.dart';

class _MockApiClient extends Mock implements ApiClient {}

Widget _buildUpload(ApiClient api) {
  return ChangeNotifierProvider<ThemeProvider>.value(
    value: ThemeProvider(),
    child: MaterialApp(
      home: Scaffold(
        body: UploadScreen(api: api),
      ),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('未连接时显示「未连接到电脑」', (tester) async {
    final api = _MockApiClient();
    when(() => api.isConnected).thenReturn(false);

    await tester.pumpWidget(_buildUpload(api));
    await tester.pumpAndSettle();

    expect(find.text('未连接到电脑'), findsOneWidget);
  });

  testWidgets('已连接时显示「选择照片」dropzone', (tester) async {
    final api = _MockApiClient();
    when(() => api.isConnected).thenReturn(true);
    when(() => api.host).thenReturn('127.0.0.1');
    when(() => api.port).thenReturn(8900);
    when(() => api.token).thenReturn('mock_token');

    await tester.pumpWidget(_buildUpload(api));
    await tester.pumpAndSettle();

    expect(find.text('选择照片'), findsOneWidget);
    expect(find.text('点击选择要上传的照片'), findsOneWidget);
  });

  testWidgets('未选择文件时「开始上传」按钮禁用', (tester) async {
    final api = _MockApiClient();
    when(() => api.isConnected).thenReturn(true);
    when(() => api.host).thenReturn('127.0.0.1');
    when(() => api.port).thenReturn(8900);
    when(() => api.token).thenReturn('mock_token');

    await tester.pumpWidget(_buildUpload(api));
    await tester.pumpAndSettle();

    final uploadBtn = find.widgetWithText(FilledButton, '开始上传');
    expect(uploadBtn, findsOneWidget);
    final btn = tester.widget<FilledButton>(uploadBtn);
    expect(btn.onPressed, isNull);
  });

  testWidgets('「全部取消」按钮初始也禁用（无 items）', (tester) async {
    final api = _MockApiClient();
    when(() => api.isConnected).thenReturn(true);
    when(() => api.host).thenReturn('127.0.0.1');
    when(() => api.port).thenReturn(8900);
    when(() => api.token).thenReturn('mock_token');

    await tester.pumpWidget(_buildUpload(api));
    await tester.pumpAndSettle();

    final cancelBtn = find.widgetWithText(OutlinedButton, '全部取消');
    expect(cancelBtn, findsOneWidget);
    final btn = tester.widget<OutlinedButton>(cancelBtn);
    expect(btn.onPressed, isNull);
  });
}
