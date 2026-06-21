import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_client.dart';
import '../services/theme_provider.dart';
import 'connect_screen.dart';

class SettingsScreen extends StatelessWidget {
  final ApiClient api;

  const SettingsScreen({super.key, required this.api});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final themeProvider = context.watch<ThemeProvider>();

    return ListView(
      children: [
        // === 连接信息 ===
        const _SectionHeader(title: '连接信息'),
        ListTile(
          leading: Icon(Icons.wifi, color: theme.colorScheme.primary),
          title: const Text('电脑地址'),
          subtitle: Text('${api.host}:${api.port}'),
        ),
        const Divider(indent: 72),

        // === 显示 ===
        const _SectionHeader(title: '显示'),
        ListTile(
          leading: Icon(Icons.brightness_6, color: theme.colorScheme.primary),
          title: const Text('主题模式'),
          subtitle: Text(_themeLabel(themeProvider.mode)),
          trailing: SegmentedButton<ThemeMode>(
            segments: const [
              ButtonSegment(value: ThemeMode.system, label: Text('自动')),
              ButtonSegment(value: ThemeMode.light, label: Text('亮色')),
              ButtonSegment(value: ThemeMode.dark, label: Text('暗色')),
            ],
            selected: {themeProvider.mode},
            onSelectionChanged: (sel) =>
                themeProvider.setTheme(sel.first),
            style: ButtonStyle(
              visualDensity: VisualDensity.compact,
              textStyle: WidgetStateProperty.all(
                  theme.textTheme.bodySmall),
            ),
          ),
        ),
        const SizedBox(height: 8),

        // === 上传 ===
        const _SectionHeader(title: '上传'),
        _WifiOnlyToggle(api: api),
        const Divider(indent: 72),

        // === 断开连接 ===
        const _SectionHeader(title: '账户'),
        ListTile(
          leading: Icon(Icons.link_off, color: theme.colorScheme.error),
          title: Text('断开连接',
              style: TextStyle(color: theme.colorScheme.error)),
          subtitle: const Text('断开后需要重新配对'),
          onTap: () => _disconnect(context),
        ),
        const Divider(indent: 72),

        // === 关于 ===
        const _SectionHeader(title: '关于'),
        const ListTile(
          leading: Icon(Icons.info),
          title: Text('Blur Arc'),
          subtitle: Text('v1.0.0'),
        ),
        const SizedBox(height: 32),
      ],
    );
  }

  void _disconnect(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('断开连接'),
        content: const Text('确定要断开连接吗？需要重新配对才能使用。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('取消')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('确定断开')),
        ],
      ),
    );

    if (confirmed == true) {
      await api.disconnect();
      if (!context.mounted) return;
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const ConnectScreen()),
        (route) => false,
      );
    }
  }

  String _themeLabel(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.dark:
        return '深色模式';
      case ThemeMode.light:
        return '浅色模式';
      case ThemeMode.system:
        return '跟随系统';
    }
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: Theme.of(context).colorScheme.primary,
        ),
      ),
    );
  }
}

/// Wi-Fi 上传开关（持久化到 shared_preferences）
class _WifiOnlyToggle extends StatefulWidget {
  final ApiClient api;
  const _WifiOnlyToggle({required this.api});

  @override
  State<_WifiOnlyToggle> createState() => _WifiOnlyToggleState();
}

class _WifiOnlyToggleState extends State<_WifiOnlyToggle> {
  bool _wifiOnly = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() => _wifiOnly = prefs.getBool('upload_wifi_only') ?? false);
  }

  Future<void> _set(bool value) async {
    setState(() => _wifiOnly = value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('upload_wifi_only', value);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListTile(
      leading: Icon(Icons.wifi_find, color: theme.colorScheme.primary),
      title: const Text('仅在 Wi-Fi 下上传'),
      subtitle: const Text('节省移动数据流量'),
      trailing: Switch(
        value: _wifiOnly,
        onChanged: _set,
      ),
    );
  }
}
