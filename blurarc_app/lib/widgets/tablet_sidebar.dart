import 'package:flutter/material.dart';

/// 平板侧栏 — 仅在相册 tab 显示
/// 显示月份分组列表 + 收起按钮
///
/// sections 是泛型列表，每个元素至少有 (month, display, count) 三个字段
class TabletSidebar extends StatelessWidget {
  final List<dynamic> sections;
  final String? activeSection;
  final void Function(String month) onSelectSection;
  final VoidCallback onCollapse;

  const TabletSidebar({
    super.key,
    required this.sections,
    required this.onSelectSection,
    required this.onCollapse,
    this.activeSection,
  });

  int _countOf(dynamic s) {
    if (s is Map) return (s['count'] as int?) ?? 0;
    try {
      return (s.count as int);
    } catch (_) {
      return 0;
    }
  }

  String _monthOf(dynamic s) {
    if (s is Map) return s['month']?.toString() ?? '';
    try {
      return s.month as String;
    } catch (_) {
      return '';
    }
  }

  String _displayOf(dynamic s) {
    if (s is Map) return s['display']?.toString() ?? '';
    try {
      return s.display as String;
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      width: 240,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          right: BorderSide(color: theme.dividerColor, width: 0.5),
        ),
      ),
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                '相册',
                style: TextStyle(
                  fontSize: 12,
                  color: theme.colorScheme.onSurface.withAlpha(150),
                  fontWeight: FontWeight.w500,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ),
          Container(
            height: 0.5,
            color: theme.dividerColor,
          ),
          // Section list
          Expanded(
            child: sections.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(
                        '加载中...',
                        style: theme.textTheme.bodyMedium,
                      ),
                    ),
                  )
                : ListView.builder(
                    itemCount: sections.length,
                    itemBuilder: (context, index) {
                      final section = sections[index];
                      final isActive = _monthOf(section) == activeSection;
                      return _SidebarItem(
                        display: _displayOf(section),
                        count: _countOf(section),
                        isActive: isActive,
                        onTap: () => onSelectSection(_monthOf(section)),
                      );
                    },
                  ),
          ),
          // Collapse button at bottom of sidebar — 原型：纯箭头
          Container(
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(color: theme.dividerColor, width: 0.5),
              ),
            ),
            child: InkWell(
              onTap: onCollapse,
              child: Padding(
                padding:
                    const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Icon(
                      Icons.chevron_left,
                      size: 16,
                      color: theme.colorScheme.onSurface.withAlpha(120),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SidebarItem extends StatelessWidget {
  final String display;
  final int count;
  final bool isActive;
  final VoidCallback onTap;

  const _SidebarItem({
    required this.display,
    required this.count,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primary = theme.colorScheme.primary;
    final bgColor = isActive ? primary.withAlpha(15) : Colors.transparent;
    final textColor =
        isActive ? primary : theme.colorScheme.onSurface.withAlpha(180);

    return Material(
      color: bgColor,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(
            children: [
              if (isActive)
                Container(
                  width: 3,
                  height: 16,
                  margin: const EdgeInsets.only(right: 10),
                  decoration: BoxDecoration(
                    color: primary,
                    borderRadius: BorderRadius.circular(2),
                  ),
                )
              else
                const SizedBox(width: 13),
              Icon(
                Icons.calendar_today_outlined,
                size: 16,
                color: textColor.withAlpha(160),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  display,
                  style: TextStyle(
                    fontSize: 14,
                    color: textColor,
                    fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                  ),
                ),
              ),
              Text(
                '$count',
                style: TextStyle(
                  fontSize: 11,
                  color: theme.colorScheme.onSurface.withAlpha(120),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 侧栏收起后的展开按钮
class TabletSidebarExpandButton extends StatelessWidget {
  final VoidCallback onTap;

  const TabletSidebarExpandButton({super.key, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: 24,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          right: BorderSide(color: theme.dividerColor, width: 0.5),
        ),
      ),
      child: InkWell(
        onTap: onTap,
        child: Center(
          child: Icon(
            Icons.chevron_right,
            size: 16,
            color: theme.colorScheme.onSurface.withAlpha(120),
          ),
        ),
      ),
    );
  }
}
