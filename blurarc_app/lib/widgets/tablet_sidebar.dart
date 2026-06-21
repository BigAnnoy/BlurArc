import 'package:flutter/material.dart';
import '../models/photo_section.dart';

/// 平板侧栏 — 仅在相册 tab 显示
/// 显示月份分组列表 + 收起按钮
class TabletSidebar extends StatelessWidget {
  final List<PhotoSection> sections;
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final total = sections.fold<int>(0, (sum, s) => sum + s.count);

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
          Container(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                Icon(
                  Icons.photo_library,
                  color: theme.colorScheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '相册 · $total 张',
                    style: theme.textTheme.titleMedium,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
          Container(
            height: 1,
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
                      final isActive = section.month == activeSection;
                      return _SidebarItem(
                        section: section,
                        isActive: isActive,
                        onTap: () => onSelectSection(section.month),
                      );
                    },
                  ),
          ),
          // Collapse button at bottom of sidebar
          Container(
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(color: theme.dividerColor, width: 0.5),
              ),
            ),
            child: InkWell(
              onTap: onCollapse,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                    vertical: 12, horizontal: 16),
                child: Row(
                  children: [
                    Icon(
                      Icons.chevron_left,
                      size: 16,
                      color: theme.colorScheme.onSurface.withAlpha(120),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '收起',
                      style: TextStyle(
                        fontSize: 12,
                        color:
                            theme.colorScheme.onSurface.withAlpha(120),
                      ),
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
  final PhotoSection section;
  final bool isActive;
  final VoidCallback onTap;

  const _SidebarItem({
    required this.section,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bgColor = isActive
        ? theme.colorScheme.primary.withAlpha(25)
        : Colors.transparent;
    final textColor = isActive
        ? theme.colorScheme.primary
        : theme.colorScheme.onSurface;

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
                  margin: const EdgeInsets.only(right: 8),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primary,
                    borderRadius: BorderRadius.circular(2),
                  ),
                )
              else
                const SizedBox(width: 11),
              Expanded(
                child: Text(
                  section.display,
                  style: TextStyle(
                    fontSize: 14,
                    color: textColor,
                    fontWeight:
                        isActive ? FontWeight.w600 : FontWeight.normal,
                  ),
                ),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: theme.dividerColor,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '${section.count}',
                  style: TextStyle(
                    fontSize: 11,
                    color: theme.colorScheme.onSurface.withAlpha(150),
                  ),
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
