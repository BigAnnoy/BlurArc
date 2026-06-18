library;

import 'package:flutter/material.dart';
import '../models/upload_item.dart';

class UploadProgressList extends StatelessWidget {
  final List<UploadItem> items;

  const UploadProgressList({super.key, required this.items});

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        return _UploadProgressItem(item: item);
      },
    );
  }
}

class _UploadProgressItem extends StatelessWidget {
  final UploadItem item;

  const _UploadProgressItem({required this.item});

  IconData _statusIcon() => switch (item.status) {
        UploadStatus.pending => Icons.schedule,
        UploadStatus.uploading => Icons.cloud_upload,
        UploadStatus.done => Icons.check_circle,
        UploadStatus.error => Icons.error,
      };

  Color _statusColor() => switch (item.status) {
        UploadStatus.pending => Colors.grey,
        UploadStatus.uploading => const Color(0xFF22D3EE),
        UploadStatus.done => Colors.green,
        UploadStatus.error => Colors.red,
      };

  String _formatSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(_statusIcon(), color: _statusColor()),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name,
                    style: const TextStyle(fontSize: 14),
                    overflow: TextOverflow.ellipsis),
                if (item.size > 0)
                  Text(_formatSize(item.size),
                      style: const TextStyle(fontSize: 12, color: Colors.grey)),
                if (item.status == UploadStatus.uploading)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: LinearProgressIndicator(
                      value: item.progress,
                      backgroundColor: Colors.grey[800],
                      valueColor:
                          const AlwaysStoppedAnimation<Color>(Color(0xFF22D3EE)),
                    ),
                  ),
                if (item.status == UploadStatus.error && item.error != null)
                  Text(item.error!,
                      style: const TextStyle(fontSize: 12, color: Colors.red),
                      overflow: TextOverflow.ellipsis),
              ],
            ),
          ),
          if (item.status == UploadStatus.uploading)
            Text('${(item.progress * 100).toStringAsFixed(0)}%',
                style: const TextStyle(fontSize: 12, color: Color(0xFF22D3EE))),
        ],
      ),
    );
  }
}
