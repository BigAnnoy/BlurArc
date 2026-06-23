import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:path_provider/path_provider.dart';
import 'package:video_player/video_player.dart';
import '../models/photo.dart';
import '../services/api_client.dart';

class PhotoPreviewScreen extends StatefulWidget {
  final List<Photo> photos;
  final int initialIndex;
  final ApiClient api;

  const PhotoPreviewScreen({
    super.key,
    required this.photos,
    required this.initialIndex,
    required this.api,
  });

  @override
  State<PhotoPreviewScreen> createState() => _PhotoPreviewScreenState();
}

class _PhotoPreviewScreenState extends State<PhotoPreviewScreen> {
  late PageController _pageController;
  int _currentIndex = 0;
  VideoPlayerController? _videoController;
  bool _showInfo = false;
  bool _downloading = false;
  double _downloadProgress = 0;

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialIndex;
    _pageController = PageController(initialPage: widget.initialIndex);
    _initVideoIfNeeded();
  }

  @override
  void dispose() {
    _pageController.dispose();
    _videoController?.dispose();
    super.dispose();
  }

  void _initVideoIfNeeded() {
    final photo = widget.photos[_currentIndex];
    if (photo.isVideo) {
      _videoController?.dispose();
      final url = widget.api.getFileUrl(photo.path);
      _videoController = VideoPlayerController.networkUrl(Uri.parse(url));
      _videoController!.initialize().then((_) {
        if (mounted) {
          setState(() {});
          _videoController!.play();
        }
      });
    } else {
      _videoController?.dispose();
      _videoController = null;
    }
  }

  void _onPageChanged(int index) {
    setState(() {
      _currentIndex = index;
      _showInfo = false;
    });
    _initVideoIfNeeded();
  }

  String _formatSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  // 下载当前照片的原图到手机本地（应用专属外存/Downloads 文件夹）
  // - Android: 写入 app-specific external storage 的 Downloads 子目录，
  //   兼容 Android 10+ scoped storage，无需 WRITE_EXTERNAL_STORAGE 权限
  // - iOS: 写入 app 沙箱 Documents/Downloads
  Future<void> _downloadCurrent() async {
    if (_downloading) return;
    final photo = widget.photos[_currentIndex];
    final url = widget.api.getFileUrl(photo.path);

    setState(() {
      _downloading = true;
      _downloadProgress = 0;
    });

    try {
      // 选目录
      final baseDir = await getApplicationDocumentsDirectory();
      final downloadsDir = Directory('${baseDir.path}/Downloads');
      if (!downloadsDir.existsSync()) {
        downloadsDir.createSync(recursive: true);
      }
      // 目标文件名：保留原文件名，冲突时加 _1/_2 后缀
      var targetName = photo.name;
      var file = File('${downloadsDir.path}/$targetName');
      var idx = 1;
      while (file.existsSync()) {
        final ext = photo.name.contains('.')
            ? photo.name.substring(photo.name.lastIndexOf('.'))
            : '';
        final stem = photo.name.contains('.')
            ? photo.name.substring(0, photo.name.lastIndexOf('.'))
            : photo.name;
        targetName = '$stem ($idx)$ext';
        file = File('${downloadsDir.path}/$targetName');
        idx++;
      }

      // 用独立的 Dio 实例下载原始文件
      final dio = Dio();
      await dio.download(
        url,
        file.path,
        onReceiveProgress: (received, total) {
          if (total > 0 && mounted) {
            setState(() => _downloadProgress = received / total);
          }
        },
        options: Options(
          responseType: ResponseType.bytes,
          followRedirects: true,
          validateStatus: (s) => s != null && s < 400,
        ),
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('已保存到: ${file.path}'),
          duration: const Duration(seconds: 4),
          action: SnackBarAction(label: '好', onPressed: () {}),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('下载失败: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _downloading = false;
          _downloadProgress = 0;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final photo = widget.photos[_currentIndex];

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(photo.name),
        actions: [
          IconButton(
            tooltip: '下载原图',
            icon: _downloading
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      value: _downloadProgress > 0 ? _downloadProgress : null,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.download_outlined),
            onPressed: _downloading ? null : _downloadCurrent,
          ),
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () => setState(() => _showInfo = !_showInfo),
          ),
        ],
      ),
      body: Stack(
        children: [
          PageView.builder(
            controller: _pageController,
            itemCount: widget.photos.length,
            onPageChanged: _onPageChanged,
            itemBuilder: (context, index) {
              final p = widget.photos[index];
              if (p.isVideo &&
                  _videoController != null &&
                  index == _currentIndex) {
                return Center(
                  child: _videoController!.value.isInitialized
                      ? AspectRatio(
                          aspectRatio: _videoController!.value.aspectRatio,
                          child: VideoPlayer(_videoController!),
                        )
                      : const CircularProgressIndicator(),
                );
              }
              return InteractiveViewer(
                minScale: 0.5,
                maxScale: 4.0,
                child: CachedNetworkImage(
                  imageUrl: widget.api.getPreviewUrl(p.path),
                  fit: BoxFit.contain,
                  placeholder: (_, __) =>
                      const Center(child: CircularProgressIndicator()),
                  errorWidget: (_, __, ___) =>
                      const Center(child: Icon(Icons.error, color: Colors.red)),
                ),
              );
            },
          ),
          if (_showInfo)
            Positioned(
              bottom: 0,
              left: 0,
              right: 0,
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: const BoxDecoration(
                  color: Colors.black87,
                  borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(photo.name,
                        style: const TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Text('路径: ${photo.path}',
                        style:
                            const TextStyle(fontSize: 12, color: Colors.grey)),
                    Text('大小: ${_formatSize(photo.size)}',
                        style:
                            const TextStyle(fontSize: 12, color: Colors.grey)),
                    Text('日期: ${photo.date}',
                        style:
                            const TextStyle(fontSize: 12, color: Colors.grey)),
                    if (photo.isVideo && photo.duration != null)
                      Text('时长: ${photo.duration}',
                          style: const TextStyle(
                              fontSize: 12, color: Colors.grey)),
                  ],
                ),
              ),
            ),
          // Page indicator
          Positioned(
            bottom: _showInfo ? 140 : 16,
            left: 0,
            right: 0,
            child: Center(
              child: Text(
                '${_currentIndex + 1} / ${widget.photos.length}',
                style: const TextStyle(color: Colors.white54, fontSize: 14),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
