import 'package:flutter/material.dart';

/// 自定义底部 Tab 栏
/// - 52px（平板）/ 56px（手机）高
/// - icon + 文字垂直排列
/// - 选中：主色 + 顶部 2px 主色指示条
/// - 不使用 Material 3 NavigationBar
class BottomTabBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;
  final List<BottomTabItem> items;
  final bool isTablet;

  const BottomTabBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
    required this.items,
    this.isTablet = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      height: isTablet ? 52 : 56,
      decoration: BoxDecoration(
        color: theme.appBarTheme.backgroundColor,
        border: Border(
          top: BorderSide(color: theme.dividerColor, width: 0.5),
        ),
      ),
      child: Row(
        children: [
          for (int i = 0; i < items.length; i++)
            Expanded(
              child: _TabButton(
                item: items[i],
                active: i == currentIndex,
                onTap: () => onTap(i),
              ),
            ),
        ],
      ),
    );
  }
}

class BottomTabItem {
  /// Material Icon（默认使用）
  final IconData? icon;

  /// Emoji 图标（与 prototype 一致时使用）
  final String? emoji;
  final String label;

  const BottomTabItem({
    this.icon,
    this.emoji,
    required this.label,
  }) : assert(icon != null || emoji != null, 'icon 或 emoji 必须传一个');
}

class _TabButton extends StatelessWidget {
  final BottomTabItem item;
  final bool active;
  final VoidCallback onTap;

  const _TabButton({
    required this.item,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = active
        ? theme.colorScheme.primary
        : theme.colorScheme.onSurface.withAlpha(
            theme.brightness == Brightness.dark ? 130 : 80,
          );

    return InkWell(
      onTap: onTap,
      child: Stack(
        alignment: Alignment.topCenter,
        children: [
          // 顶部 2px 指示条
          if (active)
            Positioned(
              top: 0,
              child: Container(
                width: 24,
                height: 2,
                decoration: BoxDecoration(
                  color: theme.colorScheme.primary,
                  borderRadius: const BorderRadius.vertical(
                    bottom: Radius.circular(2),
                  ),
                ),
              ),
            ),
          // icon + 文字
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (item.emoji != null)
                  Text(
                    item.emoji!,
                    style: TextStyle(
                      fontSize: 20,
                      height: 1.0,
                      color: color,
                    ),
                  )
                else if (item.icon != null)
                  Icon(item.icon, size: 20, color: color)
                else
                  const SizedBox(height: 20),
                const SizedBox(height: 2),
                Text(
                  item.label,
                  style: TextStyle(
                    fontSize: 10,
                    color: color,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
