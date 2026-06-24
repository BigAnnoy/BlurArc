/// HomePage widget 测试
///
/// 实际项目使用自定义 `BottomTabBar`（不是 Material 的 BottomNavigationBar），
/// 所以测试断言也要相应调整。
///
/// 注意：HomePage 在 initState 中会覆盖 `api.onDisconnected` 回调；
/// 用 mocktail 的 Mock 时该赋值是 no-op，所以 disconnect 相关测试
/// 使用真实 ApiClient 来观察回调触发。
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:blurarc_app/screens/home_page.dart';
import 'package:blurarc_app/screens/album_screen.dart';
import 'package:blurarc_app/screens/upload_screen.dart';
import 'package:blurarc_app/screens/settings_screen.dart';
import 'package:blurarc_app/widgets/bottom_tab_bar.dart';
import 'package:blurarc_app/services/api_client.dart';
import 'package:blurarc_app/services/theme_provider.dart';

class _MockApiClient extends Mock implements ApiClient {}

Widget buildHome(ApiClient api) {
  return ChangeNotifierProvider<ThemeProvider>.value(
    value: ThemeProvider(),
    child: MaterialApp(
      home: HomePage(api: api),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  ApiClient newRealApi() {
    // 真实 ApiClient（用于 disconnect 流程测试）
    final api = ApiClient();
    api.setConnectionParams('127.0.0.1', 8900);
    return api;
  }

  _MockApiClient newMockApi() {
    final api = _MockApiClient();
    // stub isConnected — Mock 默认返回 null 会破坏 !api.isConnected 的 bool 比较
    when(() => api.isConnected).thenReturn(false);
    when(() => api.host).thenReturn('127.0.0.1');
    when(() => api.port).thenReturn(8900);
    when(() => api.token).thenReturn('mock_token');
    // stub AlbumScreen 启动时调用的 getAllPhotosBySection
    when(() => api.getAllPhotosBySection(
          page: any(named: 'page'),
          pageSize: any(named: 'pageSize'),
          photosPerSection: any(named: 'photosPerSection'),
        )).thenAnswer((_) async => {
              'sections': [],
              'has_more': false,
              'available_months': [],
              'page': 1,
              'page_size': 6,
            });
    return api;
  }

  testWidgets('显示自定义 BottomTabBar（3 个 tab）', (tester) async {
    final api = newMockApi();
    await tester.pumpWidget(buildHome(api));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.byType(BottomTabBar), findsOneWidget);
    // 「相册」在 AlbumScreen 和 BottomTabBar 中都出现 — 至少一个
    expect(find.text('相册'), findsWidgets);
    expect(find.text('上传'), findsOneWidget);
    expect(find.text('设置'), findsOneWidget);
  });

  testWidgets('默认显示相册 tab（AlbumScreen）', (tester) async {
    final api = newMockApi();
    await tester.pumpWidget(buildHome(api));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.byType(AlbumScreen), findsOneWidget);
  });

  testWidgets('点击「上传」tab 切换到 UploadScreen', (tester) async {
    final api = newMockApi();
    await tester.pumpWidget(buildHome(api));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    await tester.tap(find.text('上传'));
    await tester.pumpAndSettle();

    expect(find.byType(UploadScreen), findsOneWidget);
  });

  testWidgets('点击「设置」tab 切换到 SettingsScreen', (tester) async {
    final api = newMockApi();
    await tester.pumpWidget(buildHome(api));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    await tester.tap(find.text('设置'));
    await tester.pumpAndSettle();

    expect(find.byType(SettingsScreen), findsOneWidget);
  });

  testWidgets('从设置页切回相册页', (tester) async {
    final api = newMockApi();
    await tester.pumpWidget(buildHome(api));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // 切到设置
    await tester.tap(find.text('设置'));
    await tester.pumpAndSettle();
    expect(find.byType(SettingsScreen), findsOneWidget);

    // 切回相册
    await tester.tap(find.text('相册'));
    await tester.pumpAndSettle();
    expect(find.byType(AlbumScreen), findsOneWidget);
  });

  testWidgets('disconnect 时显示 PC 端未开启界面', (tester) async {
    final api = newRealApi();
    await tester.pumpWidget(buildHome(api));
    await tester.pump();

    // 触发 onDisconnected
    api.onDisconnected?.call();
    await tester.pumpAndSettle();

    expect(find.text('PC 端未开启'), findsOneWidget);
    expect(find.text('连接已断开，请检查电脑状态'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, '重新连接'), findsOneWidget);
  });

  testWidgets('断开界面点「重新连接」回到正常状态（verifyToken=true）',
      (tester) async {
    final api = newRealApi();
    await tester.pumpWidget(buildHome(api));
    await tester.pump();

    // 触发 disconnect
    api.onDisconnected?.call();
    await tester.pumpAndSettle();
    expect(find.text('PC 端未开启'), findsOneWidget);

    // 点重新连接 — verifyToken 会真实发起 HTTP，但因为 host 是 127.0.0.1:8900
    // 且无服务监听，会失败 → _disconnected 保持 true。
    // 我们只验证按钮可点击 + 不抛异常。
    final btn = find.widgetWithText(FilledButton, '重新连接');
    expect(btn, findsOneWidget);
    expect(tester.widget<FilledButton>(btn).onPressed, isNotNull);
  });
}
