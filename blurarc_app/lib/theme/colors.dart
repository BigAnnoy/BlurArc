/// 设计色值常量（与桌面端一致）
library;

import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // ===== Dark Theme =====
  // 页面背景 — 最深
  static const darkBgPage = Color(0xFF0c1117);
  // 卡片/容器背景
  static const darkBgCard = Color(0xFF151d26);
  // 卡片 hover/按压
  static const darkBgCardHover = Color(0xFF1a2533);
  // 分隔线/边框
  static const darkBorder = Color(0xFF1c2836);
  // 主色 — cyan
  static const darkPrimary = Color(0xFF22D3EE);
  // 次要文字
  static const darkTextSecondary = Color(0xFF94a3b8);
  // 三级文字
  static const darkTextTertiary = Color(0xFF64748b);
  // 主文字
  static const darkTextPrimary = Color(0xFFe2e8f0);
  // 导航栏背景
  static const darkNavBg = Color(0xFF151d26);

  // ===== Light Theme =====
  static const lightBgPage = Color(0xFFf5f7fa);
  static const lightBgCard = Color(0xFFFFFFFF);
  static const lightBgCardHover = Color(0xFFf1f5f9);
  static const lightBorder = Color(0xFFe2e8f0);
  static const lightPrimary = Color(0xFF0891b2);
  static const lightTextSecondary = Color(0xFF64748b);
  static const lightTextTertiary = Color(0xFF94a3b8);
  static const lightTextPrimary = Color(0xFF0f172a);
  static const lightNavBg = Color(0xFFFFFFFF);
}
