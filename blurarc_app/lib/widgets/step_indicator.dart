import 'package:flutter/material.dart';

/// 步骤指示器 — 匹配 HTML 原型样式
///
/// 活跃步骤：24x8 圆角矩形（primary 色）
/// 非活跃步骤：8x8 圆形（divider 色）
class StepIndicator extends StatelessWidget {
  final int currentStep;
  final int totalSteps;

  const StepIndicator({
    super.key,
    required this.currentStep,
    required this.totalSteps,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final activeColor = theme.colorScheme.primary;
    final inactiveColor = theme.dividerColor;

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (int i = 1; i <= totalSteps; i++) ...[
          if (i > 1) const SizedBox(width: 8),
          Container(
            width: i == currentStep ? 24 : 8,
            height: 8,
            decoration: BoxDecoration(
              color: i == currentStep ? activeColor : inactiveColor,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        ],
      ],
    );
  }
}
