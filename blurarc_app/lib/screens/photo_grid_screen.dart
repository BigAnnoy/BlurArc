import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../models/photo.dart';
import '../widgets/photo_card.dart';
import 'photo_preview_screen.dart';

class PhotoGridScreen extends StatefulWidget {
  final String path;
  final ApiClient api;

  const PhotoGridScreen({super.key, required this.path, required this.api});

  @override
  State<PhotoGridScreen> createState() => _PhotoGridScreenState();
}

class _PhotoGridScreenState extends State<PhotoGridScreen> {
  List<Photo> _photos = [];
  int _totalCount = 0;
  int _currentPage = 1;
  bool _loading = true;
  bool _loadingMore = false;
  final ScrollController _scrollController = ScrollController();

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

  Future<void> _loadPhotos() async {
    setState(() => _loading = true);
    try {
      final data = await widget.api.getPhotos(widget.path);
      final photos = (data['photos'] as List? ?? [])
          .map((p) => Photo.fromJson(p as Map<String, dynamic>))
          .toList();
      setState(() {
        _photos = photos;
        _totalCount = data['count'] ?? 0;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Future<void> _loadMore() async {
    if (_loadingMore || _photos.length >= _totalCount) return;
    setState(() => _loadingMore = true);
    try {
      _currentPage++;
      final data = await widget.api.getPhotos(widget.path, page: _currentPage);
      final more = (data['photos'] as List? ?? [])
          .map((p) => Photo.fromJson(p as Map<String, dynamic>))
          .toList();
      setState(() {
        _photos.addAll(more);
        _totalCount = data['count'] ?? _totalCount;
        _loadingMore = false;
      });
    } catch (_) {
      _currentPage--;
      setState(() => _loadingMore = false);
    }
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      _loadMore();
    }
  }

  int _getCrossAxisCount(double width) {
    if (width > 900) return 6;
    if (width > 600) return 4;
    return 3;
  }

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final crossAxisCount = _getCrossAxisCount(width);

    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_photos.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.photo_library_outlined, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('此文件夹没有照片', style: TextStyle(color: Colors.grey)),
          ],
        ),
      );
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Text('$_totalCount 张照片',
                  style: const TextStyle(fontSize: 14, color: Colors.grey)),
              if (_loadingMore)
                const Padding(
                  padding: EdgeInsets.only(left: 8),
                  child: SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
            ],
          ),
        ),
        Expanded(
          child: GridView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.all(8),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: crossAxisCount,
              crossAxisSpacing: 4,
              mainAxisSpacing: 4,
            ),
            itemCount: _photos.length,
            itemBuilder: (context, index) {
              final photo = _photos[index];
              return PhotoCard(
                photo: photo,
                api: widget.api,
                onTap: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => PhotoPreviewScreen(
                        photos: _photos,
                        initialIndex: index,
                        api: widget.api,
                      ),
                    ),
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }
}
