/// 月份照片页
/// 点击某个月份后加载该月的照片网格
library;

import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../models/photo.dart';
import 'photo_preview_screen.dart';

class MonthPhotoScreen extends StatefulWidget {
  final ApiClient api;
  final String month;
  final String displayName;

  const MonthPhotoScreen({
    super.key,
    required this.api,
    required this.month,
    required this.displayName,
  });

  @override
  State<MonthPhotoScreen> createState() => _MonthPhotoScreenState();
}

class _MonthPhotoScreenState extends State<MonthPhotoScreen> {
  final List<_MonthPhotoItem> _photos = [];
  bool _loading = true;
  bool _hasMore = true;
  int _page = 1;
  int _total = 0;
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _loadPhotos();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
            _scrollController.position.maxScrollExtent - 300 &&
        _hasMore &&
        !_loading) {
      _loadMore();
    }
  }

  Future<void> _loadPhotos() async {
    setState(() => _loading = true);
    try {
      final data = await widget.api.getPhotosByMonth(widget.month, page: 1);
      _total = data['count'] ?? 0;
      final photos = (data['photos'] as List? ?? [])
          .map((p) => _MonthPhotoItem.fromJson(p as Map<String, dynamic>))
          .toList();
      setState(() {
        _photos.clear();
        _photos.addAll(photos);
        _hasMore = data['total_pages'] > 1;
        _page = 1;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Future<void> _loadMore() async {
    if (!_hasMore || _loading) return;
    setState(() => _loading = true);
    try {
      final data = await widget.api.getPhotosByMonth(widget.month, page: _page + 1);
      final photos = (data['photos'] as List? ?? [])
          .map((p) => _MonthPhotoItem.fromJson(p as Map<String, dynamic>))
          .toList();
      setState(() {
        _photos.addAll(photos);
        _hasMore = data['total_pages'] > _page + 1;
        _page += 1;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  void _openPhoto(int index) {
    // Build flat photo list for preview
    final photoList = _photos.map((p) => Photo(
      id: p.path,
      name: p.filename,
      path: p.path,
      size: 0,
      date: widget.month,
      type: p.isVideo ? 'video' : 'photo',
    )).toList();

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => PhotoPreviewScreen(
          api: widget.api,
          photos: photoList,
          initialIndex: index,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.displayName} (${_total > 0 ? _total : ""})'),
      ),
      body: _loading && _photos.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : _photos.isEmpty
              ? const Center(child: Text('暂无照片'))
              : RefreshIndicator(
                  onRefresh: _loadPhotos,
                  child: GridView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(2),
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 3,
                      crossAxisSpacing: 2,
                      mainAxisSpacing: 2,
                      childAspectRatio: 1,
                    ),
                    itemCount: _photos.length + (_hasMore ? 1 : 0),
                    itemBuilder: (context, index) {
                      if (index >= _photos.length) {
                        return const Center(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        );
                      }
                      final photo = _photos[index];
                      return _PhotoGridItem(
                        photo: photo,
                        api: widget.api,
                        onTap: () => _openPhoto(index),
                      );
                    },
                  ),
                ),
    );
  }
}

class _MonthPhotoItem {
  final String path;
  final String thumbnail;
  final bool isVideo;
  final String filename;

  _MonthPhotoItem({
    required this.path,
    required this.thumbnail,
    required this.isVideo,
    required this.filename,
  });

  factory _MonthPhotoItem.fromJson(Map<String, dynamic> json) =>
      _MonthPhotoItem(
        path: json['path'] ?? '',
        thumbnail: json['thumbnail'] ?? '',
        isVideo: json['is_video'] ?? false,
        filename: json['filename'] ?? '',
      );
}

class _PhotoGridItem extends StatelessWidget {
  final _MonthPhotoItem photo;
  final ApiClient api;
  final VoidCallback onTap;

  const _PhotoGridItem({
    required this.photo,
    required this.api,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Stack(
        fit: StackFit.expand,
        children: [
          Image.network(
            api.getThumbnailUrl(photo.path),
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Container(
              color: Theme.of(context).colorScheme.surface,
              child: const Icon(Icons.broken_image, size: 32),
            ),
            loadingBuilder: (_, child, progress) {
              if (progress == null) return child;
              return Container(
                color: Theme.of(context).colorScheme.surface,
                child: const Center(
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              );
            },
          ),
          if (photo.isVideo)
            Positioned(
              right: 4,
              bottom: 4,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.play_arrow, size: 12, color: Colors.white),
                    SizedBox(width: 2),
                    Text('视频',
                        style: TextStyle(fontSize: 10, color: Colors.white)),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
