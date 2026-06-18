class Photo {
  final String id;
  final String name;
  final String path;
  final int size;
  final String date;
  final String type; // 'photo' | 'video'
  final String? duration;

  Photo({
    required this.id,
    required this.name,
    required this.path,
    required this.size,
    required this.date,
    required this.type,
    this.duration,
  });

  factory Photo.fromJson(Map<String, dynamic> json) => Photo(
        id: json['id']?.toString() ?? '',
        name: json['name'] ?? '',
        path: json['path'] ?? '',
        size: json['size'] ?? 0,
        date: json['date'] ?? '',
        type: json['type'] ?? 'photo',
        duration: json['duration'],
      );

  bool get isVideo => type == 'video';
}
