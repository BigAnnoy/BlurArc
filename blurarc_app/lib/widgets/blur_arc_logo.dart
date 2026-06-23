import 'package:flutter/material.dart';

/// 标题栏 Logo + 文字组合（PNG 图片版）
///
/// 使用预渲染的 PNG 图片（1.5x DPI），避免 flutter_svg 的 SVG 兼容性问题。
class BlurArcLogoWithText extends StatelessWidget {
  final double height;

  const BlurArcLogoWithText({
    super.key,
    this.height = 52,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Image.asset(
      isDark
          ? 'assets/images/title_bar_dark.png'
          : 'assets/images/title_bar_light.png',
      height: height,
      filterQuality: FilterQuality.high,
    );
  }
}

/// 纯 Logo 图标（PNG 版，用于需要单独图标的场景）
class BlurArcLogo extends StatelessWidget {
  final double size;

  const BlurArcLogo({super.key, this.size = 40});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Image.asset(
      isDark
          ? 'assets/logo/icon_512_light.png'
          : 'assets/logo/icon_512.png',
      width: size,
      height: size,
      filterQuality: FilterQuality.high,
    );
  }
}
