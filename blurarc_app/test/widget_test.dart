/// BlurArcApp 渲染测试
///
/// ConnectScreen 启动后会：
/// 1. 调用 `ApiClient.loadFromStorage()` 检查是否有已保存的 token
/// 2. 如果没有，调用 `_startDiscovery()` 进行 mDNS 扫描（5s 超时，测试中会静默失败）
///
/// 渲染断言：
/// - MaterialApp + Scaffold 树能正常构建
/// - AppBar 标题里包含 BlurArcLogoWithText widget（PNG 图标）
/// - 状态信息（如「未找到 Blur Arc 服务，请手动输入」或「正在扫描局域网...」）能渲染
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:blurarc_app/main.dart';
import 'package:blurarc_app/services/theme_provider.dart';
import 'package:blurarc_app/widgets/blur_arc_logo.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    // 清空本地存储 → 启动时不会自动连接到 HomePage
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('BlurArcApp 渲染 ConnectScreen 顶部 logo + 状态信息',
      (WidgetTester tester) async {
    // 用真实 themeProvider（不需要 load，初始化默认 system 模式）
    final themeProvider = ThemeProvider();
    await tester.pumpWidget(BlurArcApp(themeProvider: themeProvider));
    // 让 initState / _checkStoredToken 的 microtask 跑完
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // 1. MaterialApp / Scaffold 树存在
    expect(find.byType(MaterialApp), findsOneWidget);
    expect(find.byType(Scaffold), findsOneWidget);

    // 2. AppBar 标题里是 BlurArcLogoWithText（不是 Text）
    expect(find.byType(BlurArcLogoWithText), findsOneWidget);

    // 3. 状态信息（"正在扫描..." / "未找到 Blur Arc 服务..." / 步骤文本）至少一个存在
    // mDNS 扫描在测试环境会 timeout，最终落到 "未找到 Blur Arc 服务，请手动输入"
    final statusCandidates = [
      '正在扫描局域网...',
      '未找到 Blur Arc 服务，请手动输入',
      '步骤 1/2：连接设备',
    ];
    final hasAnyStatus =
        statusCandidates.any((t) => find.text(t).evaluate().isNotEmpty);
    expect(hasAnyStatus, isTrue,
        reason: '期望 ConnectScreen 显示一个扫描/错误状态文本');
  });
}
