/// 文件夹入口 model
class FolderEntry {
  final String name;
  final String path;
  final int photoCount;

  FolderEntry({
    required this.name,
    required this.path,
    required this.photoCount,
  });

  factory FolderEntry.fromJson(Map<String, dynamic> json) => FolderEntry(
        name: json['name'] ?? '',
        path: json['path'] ?? '',
        photoCount: json['photo_count'] ?? 0,
      );
}

/// 面包屑节点
class BreadcrumbNode {
  final String name;
  final String path;

  BreadcrumbNode({required this.name, required this.path});

  factory BreadcrumbNode.fromJson(Map<String, dynamic> json) => BreadcrumbNode(
        name: json['name'] ?? '',
        path: json['path'] ?? '',
      );
}
