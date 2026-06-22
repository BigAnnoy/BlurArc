/// 主页（三 Tab）：相册 / 上传 / 设置
///
/// 设计（与原型图一致）：
/// - 自定义 AppBar：居中 logo + "Blur Arc" 文字
/// - 自定义 BottomTabBar：52px（平板）/ 56px（手机）
/// - 切换到非相册 Tab 时侧栏隐藏（侧栏由 AlbumScreen 内部实现）
library;

import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../widgets/blur_arc_logo.dart';
import '../widgets/bottom_tab_bar.dart';
import 'album_screen.dart';
import 'upload_screen.dart';
import 'settings_screen.dart';

class HomePage extends StatefulWidget {
  final ApiClient api;

  const HomePage({super.key, required this.api});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _currentIndex = 0;
  bool _disconnected = false;

  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    widget.api.onDisconnected = () {
      if (mounted) setState(() => _disconnected = true);
    };
    _pages = [
      AlbumScreen(api: widget.api),
      UploadScreen(api: widget.api),
      SettingsScreen(api: widget.api),
    ];
  }

  Future<void> _reconnect() async {
    final valid = await widget.api.verifyToken();
    if (valid && mounted) {
      setState(() => _disconnected = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_disconnected) {
      return Scaffold(
        appBar: _buildAppBar(),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.wifi_off, size: 64, color: Colors.grey),
                  const SizedBox(height: 16),
                  const Text('PC 端未开启',
                      style:
                          TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  const Text(
                    '连接已断开，请检查电脑状态',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 14, color: Colors.grey),
                  ),
                  const SizedBox(height: 24),
                  FilledButton.icon(
                    onPressed: _reconnect,
                    icon: const Icon(Icons.refresh),
                    label: const Text('重新连接'),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    final isTablet = MediaQuery.of(context).size.width > 600;

    return Scaffold(
      appBar: _buildAppBar(),
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: BottomTabBar(
        currentIndex: _currentIndex,
        onTap: (i) => setState(() => _currentIndex = i),
        isTablet: isTablet,
        items: const [
          BottomTabItem(icon: Icons.photo_library_outlined, label: '相册'),
          BottomTabItem(icon: Icons.cloud_upload_outlined, label: '上传'),
          BottomTabItem(icon: Icons.settings_outlined, label: '设置'),
        ],
      ),
    );
  }

  /// 自定义 AppBar — 与原型一致：居中 logo + 文字
  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      toolbarHeight: 52,
      title: const BlurArcLogoWithText(),
      centerTitle: true,
      elevation: 0,
      scrolledUnderElevation: 0,
    );
  }
}
