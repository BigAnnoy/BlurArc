/// 照片分组 model（按月分组，不携带照片列表）
class PhotoSection {
  final String month;
  final String display;
  final int count;

  PhotoSection({
    required this.month,
    required this.display,
    required this.count,
  });

  factory PhotoSection.fromJson(Map<String, dynamic> json) => PhotoSection(
        month: json['month'] ?? '',
        display: json['display'] ?? '',
        count: json['count'] ?? 0,
      );
}
