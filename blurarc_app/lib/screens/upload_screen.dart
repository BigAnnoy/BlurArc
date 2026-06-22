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
            Icon(Icons.cloud_off,
                size: 48, color: theme.colorScheme.onSurface.withAlpha(80)),
            const SizedBox(height: 12),
            Text('未连接到电脑',
                style: TextStyle(
                    color: theme.colorScheme.onSurface.withAlpha(150))),
          ],
        ),
      );
    }

    final pendingCount =
        _items.where((i) => i.status == UploadStatus.pending).length;
    final isTablet = MediaQuery.of(context).size.width > 600;

    return Column(
      children: [
        // 上传区域（dropzone + 列表）
        Expanded(
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(
                isTablet ? 16 : 12, 16, isTablet ? 16 : 12, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 大虚线框 dropzone
                _buildDropzone(theme),
                const SizedBox(height: 16),
                // 文件列表
                if (_items.isNotEmpty) _buildUploadList(),
              ],
            ),
          ),
        ),
        // 底部主次按钮（fixed）
        _buildBottomActions(theme, pendingCount),
      ],
    );
  }

  // ===== Dropzone =====
  Widget _buildDropzone(ThemeData theme) {
    return InkWell(
      onTap: _isUploading ? null : _pickFiles,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 20),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: theme.colorScheme.onSurface.withAlpha(30),
            width: 2,
            style: BorderStyle.solid,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.add_photo_alternate,
              size: 40,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(height: 8),
            Text(
              '选择照片',
              style: TextStyle(
                fontSize: 15,
                color: theme.colorScheme.onSurface,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              '点击选择要上传的照片，支持 JPEG/PNG/HEIC/视频',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 12,
                color: theme.colorScheme.onSurface.withAlpha(120),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ===== Upload List =====
  Widget _buildUploadList() {
    return UploadProgressList(items: _items);
  }

  // ===== Bottom Actions =====
  Widget _buildBottomActions(ThemeData theme, int pendingCount) {
    final isTablet = MediaQuery.of(context).size.width > 600;
    if (_isUploading) {
      return SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: LinearProgressIndicator(
            value: _items.isEmpty ? 0 : _totalProgress,
            minHeight: 4,
          ),
        ),
      );
    }

    final hasItems = _items.isNotEmpty;
    final canStart = pendingCount > 0;

    // 按钮定义（与原型一致：主按钮"开始上传"在前，次按钮"全部取消"在后）
    final primaryBtn = Expanded(
      child: FilledButton(
        onPressed: canStart ? _startUpload : null,
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 10),
          backgroundColor: canStart
              ? theme.colorScheme.primary
              : theme.colorScheme.primary.withAlpha(80),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
        child: Text(
          canStart ? '开始上传 ($pendingCount)' : '开始上传',
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );

    final secondaryBtn = Expanded(
      child: OutlinedButton(
        onPressed: hasItems ? _clearAll : null,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 10),
          side: BorderSide(
            color: hasItems
                ? theme.dividerColor
                : theme.dividerColor.withAlpha(80),
            width: 1,
          ),
          foregroundColor:
              theme.colorScheme.onSurface.withAlpha(hasItems ? 200 : 80),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
        child: const Text('全部取消',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
      ),
    );

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          top: BorderSide(color: theme.dividerColor, width: 0.5),
        ),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.all(12),
          // 原型 mobile: 上下堆叠 (column); tablet: 左右并排 (row)
          child: isTablet
              ? Row(
                  children: [
                    primaryBtn,
                    const SizedBox(width: 8),
                    secondaryBtn,
                  ],
                )
              : Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    primaryBtn,
                    const SizedBox(height: 10),
                    secondaryBtn,
                  ],
                ),
        ),
      ),
    );
  }

  double get _totalProgress {
    if (_items.isEmpty) return 0;
    return _items.fold<double>(0, (sum, i) => sum + i.progress) / _items.length;
  }

  Future<void> _pickFiles() async {
    final pickedFiles = <XFile>[];

    try {
      final images = await _picker.pickMultiImage();
      pickedFiles.addAll(images);
    } catch (_) {
      try {
        final img = await _picker.pickImage(source: ImageSource.gallery);
        if (img != null) pickedFiles.add(img);
      } catch (_) {}
    }

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

    final successCount =
        _items.where((i) => i.status == UploadStatus.done).length;
    if (successCount > 0) {
      api.uploadDone();
    }

    if (mounted && successCount > 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('上传完成: $successCount/${_items.length}')),
      );
    }
  }

  void _clearAll() {
    setState(() => _items.clear());
  }
}
