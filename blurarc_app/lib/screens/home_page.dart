/// 主页（三 Tab）：相册 / 上传 / 设置
/// 手机版：底部 Tab + IndexedStack
/// 平板版：底部 Tab + IndexedStack（侧栏由各页面内部实现）
library;

import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../widgets/blur_arc_logo.dart';
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
        appBar: AppBar(
          title: const BlurArcLogoWithText(logoSize: 24, fontSize: 14),
          centerTitle: true,
          elevation: 0,
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.wifi_off, size: 64, color: Colors.grey),
                const SizedBox(height: 16),
                const Text('PC 端未开启',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
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
      );
    }

    final isTablet = MediaQuery.of(context).size.width > 600;

    return Scaffold(
      appBar: AppBar(
        title: const BlurArcLogoWithText(logoSize: 24, fontSize: 14),
        centerTitle: true,
        elevation: 0,
        scrolledUnderElevation: 0.5,
      ),
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        labelBehavior: isTablet
            ? NavigationDestinationLabelBehavior.alwaysShow
            : NavigationDestinationLabelBehavior.alwaysHide,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.photo_outlined),
            selectedIcon: Icon(Icons.photo),
            label: '相册',
          ),
          NavigationDestination(
            icon: Icon(Icons.upload_outlined),
            selectedIcon: Icon(Icons.upload),
            label: '上传',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: '设置',
          ),
        ],
      ),
    );
  }
}
