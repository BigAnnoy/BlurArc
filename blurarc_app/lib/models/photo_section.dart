/// 照片分组 model（按月分组）
class PhotoSection {
  final String month;
  final String display;
  final int count;
  final List<SectionPhoto> photos;

  PhotoSection({
    required this.month,
    required this.display,
    required this.count,
    required this.photos,
  });

  factory PhotoSection.fromJson(Map<String, dynamic> json) {
    final photosList = (json['photos'] as List? ?? [])
        .map((p) => SectionPhoto.fromJson(p as Map<String, dynamic>))
        .toList();
    return PhotoSection(
      month: json['month'] ?? '',
      display: json['display'] ?? '',
      count: json['count'] ?? 0,
      photos: photosList,
    );
  }
}

class SectionPhoto {
  final String path;
  final String thumbnail;
  final bool isVideo;
  final String filename;

  SectionPhoto({
    required this.path,
    required this.thumbnail,
    required this.isVideo,
    required this.filename,
  });

  factory SectionPhoto.fromJson(Map<String, dynamic> json) => SectionPhoto(
        path: json['path'] ?? '',
        thumbnail: json['thumbnail'] ?? '',
        isVideo: json['is_video'] ?? false,
        filename: json['filename'] ?? '',
      );
}
