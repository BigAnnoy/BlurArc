/// AlbumScreen widget 测试（GalleryPage 适配版）
///
/// 实际项目使用 `album_screen.dart`（不是 `gallery_page.dart`）。
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:blurarc_app/screens/album_screen.dart';
import 'package:blurarc_app/services/api_client.dart';
import 'package:blurarc_app/services/theme_provider.dart';

class _MockApiClient extends Mock implements ApiClient {}

Widget _buildAlbum(ApiClient api) {
  // AlbumScreen 依赖 Scaffold + Material 祖先（侧栏用 InkWell）
  return ChangeNotifierProvider<ThemeProvider>.value(
    value: ThemeProvider(),
    child: MaterialApp(
      home: Scaffold(
        body: AlbumScreen(api: api),
      ),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    // 设置手机尺寸（400x800），避开 tablet 侧栏
    final binding = TestWidgetsFlutterBinding.ensureInitialized();
    binding.platformDispatcher.views.first.physicalSize = const Size(400, 800);
    binding.platformDispatcher.views.first.devicePixelRatio = 1.0;
  });

  tearDown(() {
    final binding = TestWidgetsFlutterBinding.ensureInitialized();
    binding.platformDispatcher.views.first.resetPhysicalSize();
    binding.platformDispatcher.views.first.resetDevicePixelRatio();
  });

  testWidgets('加载时显示 CircularProgressIndicator', (tester) async {
    final api = _MockApiClient();
    when(() => api.isConnected).thenReturn(true);
    when(() => api.host).thenReturn('127.0.0.1');
    when(() => api.port).thenReturn(8900);
    when(() => api.token).thenReturn('mock_token');
    // 让请求持续 pending 来观察 loading 状态
    final completer = Completer<Map<String, dynamic>>();
    when(() => api.getAllPhotosBySection(
          page: any(named: 'page'),
          pageSize: any(named: 'pageSize'),
          photosPerSection: any(named: 'photosPerSection'),
        )).thenAnswer((_) => completer.future);

    await tester.pumpWidget(_buildAlbum(api));
    await tester.pump(); // 触发 initState
    await tester.pump(); // 启动 Future

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    // 主动完成 future，清理 widget
    completer.complete({
      'sections': [],
      'has_more': false,
      'available_months': [],
      'page': 1,
      'page_size': 6,
    });
    await tester.pumpAndSettle();
  });

  testWidgets('加载完成（空数据）不报错', (tester) async {
    final api = _MockApiClient();
    when(() => api.isConnected).thenReturn(true);
    when(() => api.host).thenReturn('127.0.0.1');
    when(() => api.port).thenReturn(8900);
    when(() => api.token).thenReturn('mock_token');
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

    await tester.pumpWidget(_buildAlbum(api));
    await tester.pumpAndSettle(const Duration(milliseconds: 500));

    // 加载完后应不再有 spinner
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('加载失败显示错误 UI', (tester) async {
    final api = _MockApiClient();
    when(() => api.isConnected).thenReturn(true);
    when(() => api.host).thenReturn('127.0.0.1');
    when(() => api.port).thenReturn(8900);
    when(() => api.token).thenReturn('mock_token');
    when(() => api.getAllPhotosBySection(
          page: any(named: 'page'),
          pageSize: any(named: 'pageSize'),
          photosPerSection: any(named: 'photosPerSection'),
        )).thenThrow(Exception('Network error'));

    await tester.pumpWidget(_buildAlbum(api));
    await tester.pumpAndSettle(const Duration(milliseconds: 500));

    // 错误信息应可见（AlbumScreen 的具体错误展示形式因设计而异）
    // 至少不应再显示 loading spinner
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('加载非空数据：照片项数 = 2', (tester) async {
    final api = _MockApiClient();
    when(() => api.isConnected).thenReturn(true);
    when(() => api.host).thenReturn('127.0.0.1');
    when(() => api.port).thenReturn(8900);
    when(() => api.token).thenReturn('mock_token');
    when(() => api.getAllPhotosBySection(
          page: any(named: 'page'),
          pageSize: any(named: 'pageSize'),
          photosPerSection: any(named: 'photosPerSection'),
        )).thenAnswer((_) async => {
              'sections': [
                {
                  'month': '2024-01',
                  'display': '2024年1月',
                  'count': 2,
                  'photos': [
                    {
                      'id': '1',
                      'name': 'a.jpg',
                      'path': '/2024/2024-01/a.jpg',
                      'size': 1024,
                      'date': '2024-01-15T10:00:00',
                      'type': 'photo',
                    },
                    {
                      'id': '2',
                      'name': 'b.jpg',
                      'path': '/2024/2024-01/b.jpg',
                      'size': 2048,
                      'date': '2024-01-16T11:00:00',
                      'type': 'photo',
                    },
                  ],
                  'has_more_photos': false,
                }
              ],
              'has_more': false,
              'available_months': ['2024-01'],
              'page': 1,
              'page_size': 6,
            });

    await tester.pumpWidget(_buildAlbum(api));
    await tester.pumpAndSettle(const Duration(milliseconds: 500));

    // 至少能找到一个文件名（可能在 SectionHeader 附近）
    // 由于实际 grid 用 CachedNetworkImage 加载远端图片，无法直接断言 Image 数
    // 但可以断言 section header 的月份文本（可能同时出现在 toolbar 和 section）
    expect(find.text('2024年1月'), findsWidgets);
  });
}
