import 'package:flutter/material.dart';
import 'colors.dart';

class AppTheme {
  AppTheme._();

  /// 暗色主题 — 与桌面端设计语言一致
  static ThemeData dark() {
    const scheme = ColorScheme.dark(
      primary: AppColors.darkPrimary,
      surface: AppColors.darkBgCard,
      onSurface: AppColors.darkTextPrimary,
      onPrimary: Color(0xFF0c1117),
      outline: AppColors.darkBorder,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.darkBgPage,
      // AppBar
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.darkBgPage,
        foregroundColor: AppColors.darkTextPrimary,
        elevation: 0,
        scrolledUnderElevation: 0.5,
      ),
      // Card
      cardTheme: CardThemeData(
        color: AppColors.darkBgCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.darkBorder, width: 0.5),
        ),
      ),
      // Bottom Navigation
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: AppColors.darkNavBg,
        selectedItemColor: AppColors.darkPrimary,
        unselectedItemColor: AppColors.darkTextTertiary,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),
      // Divider
      dividerTheme: const DividerThemeData(
        color: AppColors.darkBorder,
        thickness: 0.5,
      ),
      // Text
      textTheme: const TextTheme(
        titleLarge: TextStyle(color: AppColors.darkTextPrimary, fontSize: 18, fontWeight: FontWeight.w600),
        titleMedium: TextStyle(color: AppColors.darkTextPrimary, fontSize: 16, fontWeight: FontWeight.w500),
        bodyLarge: TextStyle(color: AppColors.darkTextPrimary, fontSize: 15),
        bodyMedium: TextStyle(color: AppColors.darkTextSecondary, fontSize: 14),
        bodySmall: TextStyle(color: AppColors.darkTextTertiary, fontSize: 12),
      ),
    );
  }

  /// 亮色主题
  static ThemeData light() {
    const scheme = ColorScheme.light(
      primary: AppColors.lightPrimary,
      surface: AppColors.lightBgCard,
      onSurface: AppColors.lightTextPrimary,
      onPrimary: Colors.white,
      outline: AppColors.lightBorder,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.lightBgPage,
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.lightBgPage,
        foregroundColor: AppColors.lightTextPrimary,
        elevation: 0,
        scrolledUnderElevation: 0.5,
      ),
      cardTheme: CardThemeData(
        color: AppColors.lightBgCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.lightBorder, width: 0.5),
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: AppColors.lightNavBg,
        selectedItemColor: AppColors.lightPrimary,
        unselectedItemColor: AppColors.lightTextTertiary,
        type: BottomNavigationBarType.fixed,
        elevation: 1,
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.lightBorder,
        thickness: 0.5,
      ),
      textTheme: const TextTheme(
        titleLarge: TextStyle(color: AppColors.lightTextPrimary, fontSize: 18, fontWeight: FontWeight.w600),
        titleMedium: TextStyle(color: AppColors.lightTextPrimary, fontSize: 16, fontWeight: FontWeight.w500),
        bodyLarge: TextStyle(color: AppColors.lightTextPrimary, fontSize: 15),
        bodyMedium: TextStyle(color: AppColors.lightTextSecondary, fontSize: 14),
        bodySmall: TextStyle(color: AppColors.lightTextTertiary, fontSize: 12),
      ),
    );
  }
}
