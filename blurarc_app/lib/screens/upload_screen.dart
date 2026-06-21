import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_client.dart';
import '../models/upload_item.dart';
import '../widgets/upload_progress.dart';

class UploadScreen extends StatefulWidget {
  final ApiClient? api;

  const UploadScreen({super.key, this.api});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  final _picker = ImagePicker();
  final List<UploadItem> _items = [];
  bool _isUploading = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final api = widget.api;

    if (api == null || !api.isConnected) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.cloud_off, size: 48,
                color: theme.colorScheme.onSurface.withAlpha(80)),
            const SizedBox(height: 12),
            Text('未连接到电脑',
                style: TextStyle(
                    color: theme.colorScheme.onSurface.withAlpha(120))),
          ],
        ),
      );
    }

    final pendingCount =
        _items.where((i) => i.status == UploadStatus.pending).length;

    return Column(
      children: [
        // "清空" button row (moved from AppBar.actions)
        if (_items.isNotEmpty && !_isUploading)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: _clearAll,
                  child: Text('清空',
                      style: TextStyle(color: theme.colorScheme.error)),
                ),
              ],
            ),
          ),
        // 文件选择区域
        Padding(
          padding: const EdgeInsets.all(16),
          child: InkWell(
            onTap: _isUploading ? null : _pickFiles,
            borderRadius: BorderRadius.circular(12),
            child: Container(
              width: double.infinity,
              height: 100,
              decoration: BoxDecoration(
                border: Border.all(color: theme.dividerColor, width: 1),
                borderRadius: BorderRadius.circular(12),
                color: theme.colorScheme.surface,
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.add_photo_alternate, size: 32,
                      color: theme.colorScheme.primary),
                  const SizedBox(height: 4),
                  Text('点击选择照片或视频',
                      style: theme.textTheme.bodyMedium),
                  Text('支持 JPG/PNG/MP4/MOV', style: theme.textTheme.bodySmall),
                ],
              ),
            ),
          ),
        ),
        // 统计
        if (_items.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Text('${_items.length} 个文件', style: theme.textTheme.bodySmall),
                const Spacer(),
                Text(_formatSize(_items.fold<int>(0, (sum, i) => sum + i.size)),
                    style: theme.textTheme.bodySmall),
              ],
            ),
          ),
        const Divider(height: 1),
        // 上传列表
        Expanded(
          child: _items.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.cloud_upload_outlined, size: 48,
                          color: theme.colorScheme.onSurface.withAlpha(60)),
                      const SizedBox(height: 12),
                      Text('选择文件开始上传',
                          style: TextStyle(
                              color: theme.colorScheme.onSurface.withAlpha(80))),
                    ],
                  ),
                )
              : Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: UploadProgressList(items: _items),
                ),
        ),
        // 底部操作
        if (_isUploading)
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: LinearProgressIndicator(
                value: _items.isEmpty ? 0 : _totalProgress,
              ),
            ),
          ),
        if (pendingCount > 0 && !_isUploading)
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _startUpload,
                  icon: const Icon(Icons.cloud_upload),
                  label: Text('开始上传 ($pendingCount)'),
                ),
              ),
            ),
          ),
      ],
    );
  }

  double get _totalProgress {
    if (_items.isEmpty) return 0;
    return _items.fold<double>(0, (sum, i) => sum + i.progress) / _items.length;
  }

  Future<void> _pickFiles() async {
    final pickedFiles = <XFile>[];

    // 多选图片
    try {
      final images = await _picker.pickMultiImage();
      pickedFiles.addAll(images);
    } catch (_) {
      try {
        final img = await _picker.pickImage(source: ImageSource.gallery);
        if (img != null) pickedFiles.add(img);
      } catch (_) {}
    }

    // 视频
    try {
      final video = await _picker.pickVideo(source: ImageSource.gallery);
      if (video != null) pickedFiles.add(video);
    } catch (_) {}

    if (pickedFiles.isEmpty) return;

    setState(() {
      for (final xfile in pickedFiles) {
        final file = File(xfile.path);
        final size = file.existsSync() ? file.lengthSync() : 0;
        _items.add(UploadItem(
          name: xfile.name,
          path: xfile.path,
          size: size,
        ));
      }
    });
  }

  Future<void> _startUpload() async {
    final api = widget.api;
    if (api == null) return;

    setState(() => _isUploading = true);

    for (var i = 0; i < _items.length; i++) {
      if (_items[i].status != UploadStatus.pending) continue;

      setState(() {
        _items[i] = _items[i].copyWith(
          status: UploadStatus.uploading,
          progress: 0,
        );
      });

      try {
        final file = File(_items[i].path);
        if (!file.existsSync()) {
          setState(() {
            _items[i] = _items[i].copyWith(
              status: UploadStatus.error,
              error: '文件不存在',
            );
          });
          continue;
        }

        await api.uploadFile(
          _items[i].path,
          _items[i].name,
          onProgress: (sent, total) {
            if (total > 0 && mounted) {
              setState(() {
                _items[i] = _items[i].copyWith(
                  progress: sent / total,
                );
              });
            }
          },
        );

        setState(() {
          _items[i] = _items[i].copyWith(
            status: UploadStatus.done,
            progress: 1.0,
          );
        });
      } catch (e) {
        setState(() {
          _items[i] = _items[i].copyWith(
            status: UploadStatus.error,
            error: e.toString(),
          );
        });
      }
    }

    setState(() => _isUploading = false);

    // 通知后端上传批次已完成（触发 PC 端导入弹窗）
    final successCount =
        _items.where((i) => i.status == UploadStatus.done).length;
    if (successCount > 0) {
      api.uploadDone();
    }

    // 提示完成
    if (mounted && successCount > 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('上传完成: $successCount/${_items.length}')),
      );
    }
  }

  void _clearAll() {
    setState(() => _items.clear());
  }

  String _formatSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }
}
