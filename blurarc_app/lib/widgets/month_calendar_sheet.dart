import 'package:flutter/material.dart';

/// 月份选择日历底部面板（手机版使用）
///
/// 用法：
///   MonthCalendarSheet.show(context, availableMonths: [...], onSelect: (y, m) { ... });
class MonthCalendarSheet extends StatefulWidget {
  final int initialYear;
  final List<String> availableMonths; // e.g. ['2026-06', '2026-05', ...]
  final String? selectedMonth; // e.g. '2026-06'
  final void Function(int year, int month) onSelect;

  const MonthCalendarSheet({
    super.key,
    required this.initialYear,
    required this.availableMonths,
    this.selectedMonth,
    required this.onSelect,
  });

  /// 显示日历底部面板
  static Future<void> show(
    BuildContext context, {
    required List<String> availableMonths,
    String? selectedMonth,
    required void Function(int year, int month) onSelect,
  }) {
    int currentYear = DateTime.now().year;
    if (selectedMonth != null) {
      currentYear = int.tryParse(selectedMonth.split('-')[0]) ?? currentYear;
    }

    return showModalBottomSheet(
      context: context,
      builder: (_) => MonthCalendarSheet(
        initialYear: currentYear,
        availableMonths: availableMonths,
        selectedMonth: selectedMonth,
        onSelect: onSelect,
      ),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
    );
  }

  @override
  State<MonthCalendarSheet> createState() => _MonthCalendarSheetState();
}

class _MonthCalendarSheetState extends State<MonthCalendarSheet> {
  late int _year;

  @override
  void initState() {
    super.initState();
    _year = widget.initialYear;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // 拖拽指示条
            Container(
              width: 36,
              height: 4,
              margin: const EdgeInsets.only(bottom: 4),
              decoration: BoxDecoration(
                color: theme.dividerColor,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            // 年份切换 — 原型：year-nav 包含 ‹ 按钮 + year-label + › 按钮 + ✕ 关闭按钮
            Row(
              children: [
                // Year nav
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _YearBtn(
                      icon: Icons.chevron_left,
                      onTap: () => setState(() => _year--),
                    ),
                    const SizedBox(width: 12),
                    SizedBox(
                      width: 72,
                      child: Text(
                        '$_year',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    _YearBtn(
                      icon: Icons.chevron_right,
                      onTap: () => setState(() => _year++),
                    ),
                  ],
                ),
                const Spacer(),
                // Close button
                _YearBtn(
                  icon: Icons.close,
                  onTap: () => Navigator.pop(context),
                ),
              ],
            ),
            const SizedBox(height: 12),
            // 月份网格 — 原型：4列，aspect-ratio: 1，gap: 6px
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 4,
                mainAxisSpacing: 6,
                crossAxisSpacing: 6,
                childAspectRatio: 1,
              ),
              itemCount: 12,
              itemBuilder: (context, index) {
                final month = index + 1;
                final monthStr = '$_year-${month.toString().padLeft(2, '0')}';
                final hasPhotos = widget.availableMonths.contains(monthStr);
                final isSelected = monthStr == widget.selectedMonth;

                return _MonthCell(
                  month: month,
                  hasPhotos: hasPhotos,
                  isSelected: isSelected,
                  onTap: hasPhotos
                      ? () {
                          Navigator.pop(context);
                          widget.onSelect(_year, month);
                        }
                      : null,
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _MonthCell extends StatelessWidget {
  final int month;
  final bool hasPhotos;
  final bool isSelected;
  final VoidCallback? onTap;

  const _MonthCell({
    required this.month,
    required this.hasPhotos,
    required this.isSelected,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // 原型：month-tile 包含 month-name(13px) + month-count(10px)
    // active: 背景 rgba(34,211,238,0.12)，边框 primary
    // has-photos: 文字 primary 颜色
    final bgColor = isSelected
        ? theme.colorScheme.primary.withAlpha(30)
        : Colors.transparent;
    final borderColor =
        isSelected ? theme.colorScheme.primary : Colors.transparent;
    final textColor = isSelected
        ? theme.colorScheme.primary
        : hasPhotos
            ? theme.colorScheme.onSurface
            : theme.colorScheme.onSurface.withAlpha(60);

    return GestureDetector(
      onTap: hasPhotos ? onTap : null,
      child: Container(
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: borderColor, width: 0.5),
        ),
        alignment: Alignment.center,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '$month月',
              style: TextStyle(
                color: textColor,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
            if (hasPhotos)
              Text(
                '•',
                style: TextStyle(
                  color: theme.colorScheme.primary,
                  fontSize: 10,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// 年份切换按钮（原型：28x28 圆形按钮）
class _YearBtn extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _YearBtn({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: onTap,
      customBorder: const CircleBorder(),
      child: Container(
        width: 28,
        height: 28,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: theme.dividerColor, width: 0.5),
        ),
        child: Icon(icon,
            size: 14, color: theme.colorScheme.onSurface.withAlpha(180)),
      ),
    );
  }
}
