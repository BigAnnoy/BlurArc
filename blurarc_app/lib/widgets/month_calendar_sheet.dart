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
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // 拖拽指示条
            Container(
              width: 36,
              height: 4,
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: theme.dividerColor,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            // 年份切换
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: const Icon(Icons.chevron_left),
                  onPressed: () => setState(() => _year--),
                ),
                Text('$_year 年', style: theme.textTheme.titleMedium),
                IconButton(
                  icon: const Icon(Icons.chevron_right),
                  onPressed: () => setState(() => _year++),
                ),
              ],
            ),
            const SizedBox(height: 12),
            // 月份网格
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate:
                  const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 4,
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 2.2,
              ),
              itemCount: 12,
              itemBuilder: (context, index) {
                final month = index + 1;
                final monthStr =
                    '$_year-${month.toString().padLeft(2, '0')}';
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
    final bgColor = isSelected
        ? theme.colorScheme.primary
        : hasPhotos
            ? theme.colorScheme.surface
            : theme.colorScheme.surface.withAlpha(80);
    final textColor = isSelected
        ? theme.colorScheme.onPrimary
        : hasPhotos
            ? theme.colorScheme.onSurface
            : theme.colorScheme.onSurface.withAlpha(60);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(8),
          border: isSelected
              ? null
              : Border.all(
                  color: theme.dividerColor,
                  width: 0.5,
                ),
        ),
        alignment: Alignment.center,
        child: Text(
          '$month月',
          style: TextStyle(
            color: textColor,
            fontSize: 14,
            fontWeight: isSelected || hasPhotos ? FontWeight.w500 : FontWeight.normal,
          ),
        ),
      ),
    );
  }
}
