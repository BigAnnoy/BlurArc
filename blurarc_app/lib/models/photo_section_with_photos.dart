/// 照片分组 model（含照片列表）
/// 用于连续网格展示 — 每个 section 包含自己的照片数组
class PhotoSectionWithPhotos {
  final String month;
  final String display;
  final int count;
  final List<PhotoItem> photos;
  final bool hasMorePhotos;

  PhotoSectionWithPhotos({
    required this.month,
    required this.display,
    required this.count,
    required this.photos,
    required this.hasMorePhotos,
  });

  factory PhotoSectionWithPhotos.fromJson(Map<String, dynamic> json) {
    final list = (json['photos'] as List? ?? [])
        .map((p) => PhotoItem.fromJson(p as Map<String, dynamic>))
        .toList();
    return PhotoSectionWithPhotos(
      month: json['month'] ?? '',
      display: json['display'] ?? '',
      count: json['count'] ?? 0,
      photos: list,
      hasMorePhotos: json['has_more_photos'] ?? false,
    );
  }
}

class PhotoItem {
  final String path;
  final String thumbnail;
  final bool isVideo;
  final String filename;
  final String? mediaDate;

  PhotoItem({
    required this.path,
    required this.thumbnail,
    required this.isVideo,
    required this.filename,
    this.mediaDate,
  });

  factory PhotoItem.fromJson(Map<String, dynamic> json) => PhotoItem(
        path: json['path'] ?? '',
        thumbnail: json['thumbnail'] ?? '',
        isVideo: json['is_video'] ?? false,
        filename: json['filename'] ?? '',
        mediaDate: json['media_date'],
      );
}
