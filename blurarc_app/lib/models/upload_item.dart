/// 上传任务模型
library;

enum UploadStatus { pending, uploading, done, error }

class UploadItem {
  final String name;
  final int size;
  final UploadStatus status;
  final double progress; // 0.0 ~ 1.0
  final String? error;

  UploadItem({
    required this.name,
    required this.size,
    this.status = UploadStatus.pending,
    this.progress = 0.0,
    this.error,
  });
}
