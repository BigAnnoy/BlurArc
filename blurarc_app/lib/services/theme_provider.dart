import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/app_theme.dart' as themes;

/// 主题提供者 — 管理 dark / light / system 三种模式
/// 用户选择持久化到 shared_preferences
class ThemeProvider extends ChangeNotifier {
  static const _key = 'theme_mode';

  ThemeMode _mode = ThemeMode.system;

  ThemeMode get mode => _mode;

  static final _darkTheme = themes.AppTheme.dark();
  static final _lightTheme = themes.AppTheme.light();

  /// 启动时调用：从本地存储恢复用户选择
  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString(_key);
    if (stored != null) {
      _mode = _fromString(stored);
      notifyListeners();
    }
  }

  /// 切换主题，持久化
  Future<void> setTheme(ThemeMode mode) async {
    if (mode == _mode) return;
    _mode = mode;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, _toString(mode));
  }

  /// 获取当前可用的深浅色主题数据
  ThemeData getThemeData(Brightness platformBrightness) {
    switch (_mode) {
      case ThemeMode.dark:
        return _darkTheme;
      case ThemeMode.light:
        return _lightTheme;
      case ThemeMode.system:
        return platformBrightness == Brightness.dark ? _darkTheme : _lightTheme;
    }
  }

  static ThemeMode _fromString(String s) {
    switch (s) {
      case 'dark':
        return ThemeMode.dark;
      case 'light':
        return ThemeMode.light;
      default:
        return ThemeMode.system;
    }
  }

  static String _toString(ThemeMode mode) {
    switch (mode) {
      case ThemeMode.dark:
        return 'dark';
      case ThemeMode.light:
        return 'light';
      default:
        return 'system';
    }
  }
}
