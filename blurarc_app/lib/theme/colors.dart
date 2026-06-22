/// 设计色值常量（与原型图 tablet/mobile v3 一致）
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
  // 卡片激活态（背景 + 透明度）
  static const darkBgCardActive = Color(0x14FFFFFF);
  // 分隔线/边框
  static const darkBorder = Color(0xFF1c2836);
  // 主色 — cyan
  static const darkPrimary = Color(0xFF22D3EE);
  // 主色 hover
  static const darkPrimaryHover = Color(0xFF0891B2);
  // 危险色
  static const darkDanger = Color(0xFFdc2626);
  // 主文字
  static const darkTextPrimary = Color(0xFFe8f0f5);
  // 次要文字
  static const darkTextSecondary = Color(0xFF8aa0b0);
  // 三级文字
  static const darkTextTertiary = Color(0xFF506070);
  // 导航栏背景
  static const darkNavBg = Color(0xFF151d26);

  // ===== Light Theme =====
  static const lightBgPage = Color(0xFFf5f7fa);
  static const lightBgCard = Color(0xFFFFFFFF);
  static const lightBgCardHover = Color(0xFFeef1f6);
  static const lightBgCardActive = Color(0x0F0891B2); // primary 6% alpha
  static const lightBorder = Color(0xFFe2e6ed);
  static const lightPrimary = Color(0xFF0891b2);
  static const lightPrimaryHover = Color(0xFF0e7490);
  static const lightDanger = Color(0xFFdc2626);
  static const lightTextPrimary = Color(0xFF1a2332);
  static const lightTextSecondary = Color(0xFF5a6a80);
  static const lightTextTertiary = Color(0xFF9aa5b5);
  static const lightNavBg = Color(0xFFFFFFFF);
}
