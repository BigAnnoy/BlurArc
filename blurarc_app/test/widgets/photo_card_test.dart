/// PhotoCard widget 测试
///
/// 实际项目 `PhotoCard` 构造签名：
///   PhotoCard({required photo, required api, required onTap})
/// 1. `api` 必填（用于生成缩略图 URL）
/// 2. 没有 `onLongPress` 参数
/// 3. `Photo` 模型字段：`id: String, name: String, path: String, size: int, date: String, type: String, duration: String?`
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:blurarc_app/widgets/photo_card.dart';
import 'package:blurarc_app/models/photo.dart';
import 'package:blurarc_app/services/api_client.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  Photo makePhoto({
    String id = '1',
    String name = 'test.jpg',
    String path = '/album/2024/test.jpg',
    int size = 1024000,
    String type = 'photo',
  }) =>
      Photo(
        id: id,
        name: name,
        path: path,
        size: size,
        date: '2024-01-15T10:30:00',
        type: type,
      );

  ApiClient makeApi() {
    final api = ApiClient();
    api.setConnectionParams('192.168.1.100', 8900);
    return api;
  }

  testWidgets('显示文件名和缩略图区域', (tester) async {
    final photo = makePhoto();
    final api = makeApi();

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: PhotoCard(photo: photo, api: api, onTap: () {}),
      ),
    ));
    await tester.pump();

    // 文件名显示在 PhotoCard 右下角
    expect(find.text('test.jpg'), findsOneWidget);

    // 缩略图用 CachedNetworkImage 渲染
    // 初始状态是 placeholder，显示 photo icon — 不直接断言 Image widget 数
    // 但至少能找到至少一个 Image（placeholder 或真实图片）
    expect(find.byType(Image), findsWidgets);
  });

  testWidgets('视频缩略图上叠加播放图标', (tester) async {
    final photo = makePhoto(type: 'video', name: 'clip.mp4');
    final api = makeApi();

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: PhotoCard(photo: photo, api: api, onTap: () {}),
      ),
    ));
    await tester.pump();

    // Icons.play_circle_fill
    expect(find.byIcon(Icons.play_circle_fill), findsOneWidget);
  });

  testWidgets('点击触发 onTap 回调', (tester) async {
    var tapCount = 0;
    final photo = makePhoto();
    final api = makeApi();

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: PhotoCard(
          photo: photo,
          api: api,
          onTap: () => tapCount++,
        ),
      ),
    ));
    await tester.pump();

    await tester.tap(find.byType(PhotoCard));
    await tester.pump();

    expect(tapCount, 1);
  });

  testWidgets('重复点击 3 次，tapCount = 3', (tester) async {
    var tapCount = 0;
    final photo = makePhoto();
    final api = makeApi();

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: PhotoCard(
          photo: photo,
          api: api,
          onTap: () => tapCount++,
        ),
      ),
    ));
    await tester.pump();

    await tester.tap(find.byType(PhotoCard));
    await tester.tap(find.byType(PhotoCard));
    await tester.tap(find.byType(PhotoCard));
    await tester.pump();

    expect(tapCount, 3);
  });

  testWidgets('使用 isVideo getter 正确判断类型', (tester) async {
    final photoPhoto = makePhoto(type: 'photo');
    final photoVideo = makePhoto(type: 'video');
    expect(photoPhoto.isVideo, isFalse);
    expect(photoVideo.isVideo, isTrue);
  });

  testWidgets('PhotoCard 文件名超长时显示省略号（不报错）', (tester) async {
    final longName = 'a' * 200 + '.jpg';
    final photo = makePhoto(name: longName);
    final api = makeApi();

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: SizedBox(
          width: 100,
          height: 100,
          child: PhotoCard(photo: photo, api: api, onTap: () {}),
        ),
      ),
    ));
    await tester.pump();

    expect(find.text(longName), findsOneWidget);
    // 不抛 overflow 异常
    expect(tester.takeException(), isNull);
  });
}
