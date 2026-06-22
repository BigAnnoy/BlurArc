import 'package:flutter/material.dart';
import 'colors.dart';

class AppTheme {
  AppTheme._();

  /// 暗色主题 — 与原型图 tablet/mobile v3 dark 一致
  static ThemeData dark() {
    const scheme = ColorScheme.dark(
      primary: AppColors.darkPrimary,
      onPrimary: AppColors.darkBgPage,
      surface: AppColors.darkBgCard,
      onSurface: AppColors.darkTextPrimary,
      outline: AppColors.darkBorder,
      error: AppColors.darkDanger,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.darkBgPage,
      // AppBar — 与原型 dark 一致：透明（页面背景），无可见"卡片底"色块
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.darkBgPage,
        foregroundColor: AppColors.darkTextPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        surfaceTintColor: Colors.transparent,
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
      // Bottom Navigation (用于 SwitchListTile 等)
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
        space: 0.5,
      ),
      // IconButton 主题：覆盖默认的 hover 高亮
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: AppColors.darkTextSecondary,
        ),
      ),
      // Text
      textTheme: const TextTheme(
        titleLarge: TextStyle(color: AppColors.darkTextPrimary, fontSize: 18, fontWeight: FontWeight.w600),
        titleMedium: TextStyle(color: AppColors.darkTextPrimary, fontSize: 16, fontWeight: FontWeight.w500),
        titleSmall: TextStyle(color: AppColors.darkTextSecondary, fontSize: 14, fontWeight: FontWeight.w500),
        bodyLarge: TextStyle(color: AppColors.darkTextPrimary, fontSize: 15),
        bodyMedium: TextStyle(color: AppColors.darkTextSecondary, fontSize: 14),
        bodySmall: TextStyle(color: AppColors.darkTextTertiary, fontSize: 12),
        labelLarge: TextStyle(color: AppColors.darkTextPrimary, fontSize: 14, fontWeight: FontWeight.w500),
      ),
    );
  }

  /// 亮色主题 — 与原型图 tablet/mobile v3 light 一致
  static ThemeData light() {
    const scheme = ColorScheme.light(
      primary: AppColors.lightPrimary,
      onPrimary: Colors.white,
      surface: AppColors.lightBgCard,
      onSurface: AppColors.lightTextPrimary,
      outline: AppColors.lightBorder,
      error: AppColors.lightDanger,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.lightBgPage,
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.lightBgCard,
        foregroundColor: AppColors.lightTextPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        surfaceTintColor: Colors.transparent,
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
        elevation: 0,
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.lightBorder,
        thickness: 0.5,
        space: 0.5,
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: AppColors.lightTextSecondary,
        ),
      ),
      textTheme: const TextTheme(
        titleLarge: TextStyle(color: AppColors.lightTextPrimary, fontSize: 18, fontWeight: FontWeight.w600),
        titleMedium: TextStyle(color: AppColors.lightTextPrimary, fontSize: 16, fontWeight: FontWeight.w500),
        titleSmall: TextStyle(color: AppColors.lightTextSecondary, fontSize: 14, fontWeight: FontWeight.w500),
        bodyLarge: TextStyle(color: AppColors.lightTextPrimary, fontSize: 15),
        bodyMedium: TextStyle(color: AppColors.lightTextSecondary, fontSize: 14),
        bodySmall: TextStyle(color: AppColors.lightTextTertiary, fontSize: 12),
        labelLarge: TextStyle(color: AppColors.lightTextPrimary, fontSize: 14, fontWeight: FontWeight.w500),
      ),
    );
  }
}
