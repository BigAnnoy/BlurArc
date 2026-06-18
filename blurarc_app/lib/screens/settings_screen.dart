/// 设置页面
library;

import 'package:flutter/material.dart';
import '../services/api_client.dart';

class SettingsScreen extends StatelessWidget {
  final ApiClient api;

  const SettingsScreen({super.key, required this.api});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('设置')),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.wifi),
            title: const Text('连接信息'),
            subtitle: Text('${api.host}:${api.port}'),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.refresh),
            title: const Text('重新配对'),
            onTap: () {
              // TODO: 清除 token 并回到连接页
            },
          ),
          const Divider(),
          const ListTile(
            leading: Icon(Icons.info),
            title: Text('关于'),
            subtitle: Text('Blur Arc v1.0.0'),
          ),
        ],
      ),
    );
  }
}
