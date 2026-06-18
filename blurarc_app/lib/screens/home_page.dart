/// 主页（三 Tab）：相册 / 上传 / 设置
library;

import 'package:flutter/material.dart';
import '../services/api_client.dart';
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

  late final List<Widget> _pages;

  @override
  void initState() {
    super.initState();
    _pages = [
      AlbumScreen(api: widget.api),
      const UploadScreen(),
      SettingsScreen(api: widget.api),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (i) => setState(() => _currentIndex = i),
        selectedItemColor: const Color(0xFF22D3EE),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.photo),
            label: '相册',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.upload),
            label: '上传',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings),
            label: '设置',
          ),
        ],
      ),
    );
  }
}
