import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_client.dart';
import '../services/device_info_service.dart';
import '../services/theme_provider.dart';
import 'connect_screen.dart';

class SettingsScreen extends StatefulWidget {
  final ApiClient api;

  const SettingsScreen({super.key, required this.api});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  String _deviceName = '';

  @override
  void initState() {
    super.initState();
    DeviceInfoService.getDeviceName().then((n) {
      if (mounted) setState(() => _deviceName = n);
    });
  }

  @override
  Widget build(BuildContext context) {
    final api = widget.api;
    final theme = Theme.of(context);
    final themeProvider = context.watch<ThemeProvider>();
    final isTablet = MediaQuery.of(context).size.width > 600;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // ===== 连接信息卡片 =====
        if (!isTablet) const _SettingsSectionTitle('设备信息'),
        _SettingsCard(
          child: Column(
            children: [
              _SettingsItem(
                label: '设备名称',
                value: Text(
                  _deviceName.isEmpty ? '...' : _deviceName,
                  style: const TextStyle(
                    fontSize: 13,
                    color: Color(0xFF9aa5b5),
                  ),
                ),
              ),
              const _SettingsDivider(),
              _SettingsItem(
                label: '电脑地址',
                value: Text(
                  '${api.host}:${api.port}',
                  style: const TextStyle(
                    fontSize: 13,
                    color: Color(0xFF9aa5b5),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // ===== 主题选择卡片 =====
        if (!isTablet) const _SettingsSectionTitle('显示'),
        _SettingsCard(
          child: _SettingsItem(
            label: '主题',
            customTrailing: _ThemeRadioGroup(themeProvider: themeProvider),
          ),
        ),
        const SizedBox(height: 16),

        // ===== 仅 Wi-Fi 上传 =====
        const _SettingsCard(
          child: _SettingsItem(
            label: '仅在 Wi-Fi 下上传',
            customTrailing: _WifiOnlyToggle(),
          ),
        ),
        const SizedBox(height: 16),

        // ===== 关于 =====
        if (!isTablet) const _SettingsSectionTitle('关于'),
        const _SettingsCard(
          child: _SettingsItem(
            label: 'Blur Arc',
            value: Text(
              'v1.0.0',
              style: TextStyle(fontSize: 13, color: Color(0xFF9aa5b5)),
            ),
          ),
        ),
        const SizedBox(height: 24),

        // ===== 断开连接（危险按钮） =====
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => _disconnect(context),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 12),
                side: BorderSide(
                  color: theme.colorScheme.error,
                  width: 1,
                ),
                foregroundColor: theme.colorScheme.error,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: const Text(
                '断开连接',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
              ),
            ),
          ),
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
      await widget.api.disconnect();
      if (!context.mounted) return;
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const ConnectScreen()),
        (route) => false,
      );
    }
  }
}

// ===== Settings Card 容器 =====
// 原型 mobile: background + border-radius 12 + 0.5px border (无阴影)
class _SettingsCard extends StatelessWidget {
  final Widget child;
  const _SettingsCard({required this.child});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.dividerColor,
          width: 0.5,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: child,
    );
  }
}

// ===== Settings Item =====
class _SettingsItem extends StatelessWidget {
  final String label;
  final Widget? value;
  final Widget? customTrailing;

  const _SettingsItem({
    required this.label,
    this.value,
    this.customTrailing,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontSize: 14),
            ),
          ),
          if (customTrailing != null)
            customTrailing!
          else if (value != null)
            value!,
        ],
      ),
    );
  }
}

class _SettingsDivider extends StatelessWidget {
  const _SettingsDivider();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 0.5,
      margin: const EdgeInsets.only(left: 16),
      color: Theme.of(context).dividerColor,
    );
  }
}

// ===== Settings Section Title (mobile only) =====
// 原型 mobile: 大写、letter-spacing 0.5px、字色 text-tertiary、padding 0 4px 8px
class _SettingsSectionTitle extends StatelessWidget {
  final String text;
  const _SettingsSectionTitle(this.text);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 4, 4, 8),
      child: Text(
        text.toUpperCase(),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          letterSpacing: 0.5,
          color: Theme.of(context).colorScheme.onSurface.withAlpha(120),
        ),
      ),
    );
  }
}

// ===== Theme Radio Group =====
class _ThemeRadioGroup extends StatelessWidget {
  final ThemeProvider themeProvider;
  const _ThemeRadioGroup({required this.themeProvider});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primary = theme.colorScheme.primary;
    // 原型顺序：跟随系统 / 深色 / 浅色
    final options = [
      (ThemeMode.system, '跟随系统'),
      (ThemeMode.dark, '深色'),
      (ThemeMode.light, '浅色'),
    ];
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: options.map((opt) {
        final selected = opt.$1 == themeProvider.mode;
        return Padding(
          padding: const EdgeInsets.only(left: 4),
          child: _RadioBtn(
            label: opt.$2,
            selected: selected,
            onTap: () => themeProvider.setTheme(opt.$1),
            primary: primary,
          ),
        );
      }).toList(),
    );
  }
}

class _RadioBtn extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final Color primary;

  const _RadioBtn({
    required this.label,
    required this.selected,
    required this.onTap,
    required this.primary,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Material(
      color: selected ? primary.withAlpha(15) : Colors.transparent,
      borderRadius: BorderRadius.circular(6),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(6),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: selected ? primary : theme.dividerColor,
              width: 1,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              color: selected
                  ? primary
                  : theme.colorScheme.onSurface.withAlpha(180),
              fontWeight: selected ? FontWeight.w500 : FontWeight.normal,
            ),
          ),
        ),
      ),
    );
  }
}

// ===== Wi-Fi Only Toggle =====
class _WifiOnlyToggle extends StatefulWidget {
  const _WifiOnlyToggle();

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
    if (mounted) {
      setState(() => _wifiOnly = prefs.getBool('upload_wifi_only') ?? false);
    }
  }

  Future<void> _set(bool value) async {
    setState(() => _wifiOnly = value);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('upload_wifi_only', value);
  }

  @override
  Widget build(BuildContext context) {
    return _CustomSwitch(
      value: _wifiOnly,
      onChanged: _set,
    );
  }
}

class _CustomSwitch extends StatelessWidget {
  final bool value;
  final ValueChanged<bool> onChanged;
  const _CustomSwitch({required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: () => onChanged(!value),
      borderRadius: BorderRadius.circular(13),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 44,
        height: 26,
        padding: const EdgeInsets.all(3),
        decoration: BoxDecoration(
          color: value
              ? theme.colorScheme.primary
              : theme.colorScheme.onSurface.withAlpha(20),
          borderRadius: BorderRadius.circular(13),
        ),
        child: AnimatedAlign(
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeInOut,
          alignment: value ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            width: 20,
            height: 20,
            decoration: const BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: Colors.black26,
                  blurRadius: 2,
                  offset: Offset(0, 1),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
