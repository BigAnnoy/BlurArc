/// 上传任务模型
library;

enum UploadStatus { pending, uploading, done, error }

class UploadItem {
  final String name;
  final String path; // 文件绝对路径
  final int size;
  final UploadStatus status;
  final double progress; // 0.0 ~ 1.0
  final String? error;

  UploadItem({
    required this.name,
    required this.path,
    required this.size,
    this.status = UploadStatus.pending,
    this.progress = 0.0,
    this.error,
  });

  UploadItem copyWith({
    String? name,
    String? path,
    int? size,
    UploadStatus? status,
    double? progress,
    String? error,
  }) {
    return UploadItem(
      name: name ?? this.name,
      path: path ?? this.path,
      size: size ?? this.size,
      status: status ?? this.status,
      progress: progress ?? this.progress,
      error: error,
    );
  }
}
