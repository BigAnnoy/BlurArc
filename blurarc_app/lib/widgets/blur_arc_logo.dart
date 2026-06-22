import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

class BlurArcLogo extends StatelessWidget {
  final double size;
  final Color? color;

  const BlurArcLogo({super.key, this.size = 40, this.color});

  @override
  Widget build(BuildContext context) {
    return SvgPicture.asset(
      'assets/logo/blur_arc_logo.svg',
      width: size,
      height: size,
      colorFilter:
          color != null ? ColorFilter.mode(color!, BlendMode.srcIn) : null,
    );
  }
}

class BlurArcLogoWithText extends StatelessWidget {
  final double logoSize;
  final double fontSize;
  final FontWeight fontWeight;
  final Color? color;

  const BlurArcLogoWithText({
    super.key,
    this.logoSize = 28,
    this.fontSize = 17,
    this.fontWeight = FontWeight.w600,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final c = color ?? Theme.of(context).colorScheme.primary;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        BlurArcLogo(size: logoSize, color: c),
        const SizedBox(width: 8),
        Text(
          'Blur Arc',
          style: TextStyle(
            fontSize: fontSize,
            fontWeight: fontWeight,
            color: c,
          ),
        ),
      ],
    );
  }
}
