/// 相册页面
/// 手机版：AppBar（日期跳转 + 文件夹入口）+ 分组网格
/// 平板版：左侧边栏（分组列表）+ 主体（日期跳转 + 双指缩放网格）
library;

import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../models/photo.dart';
import '../models/photo_section.dart';
import '../widgets/month_calendar_sheet.dart';
import '../widgets/tablet_sidebar.dart';
import 'folder_screen.dart';
import 'photo_preview_screen.dart';

class AlbumScreen extends StatefulWidget {
  final ApiClient api;

  const AlbumScreen({super.key, required this.api});

  @override
  State<AlbumScreen> createState() => _AlbumScreenState();
}

class _AlbumScreenState extends State<AlbumScreen> {
  List<PhotoSection> _sections = [];
  List<String> _availableMonths = [];
  bool _loading = true;
  bool _hasMore = true;
  int _page = 1;
  String _displayMonth = '';
  final _scrollController = ScrollController();

  // Pre-built flat list for PhotoPreviewScreen
  List<Photo> _allPhotos = [];

  // Tablet state
  bool _sidebarCollapsed = false;
  int _gridColumns = 5; // Tablet default columns
  double _pinchStartScale = 1.0;
  bool _pinchTriggered = false;

  @override
  void initState() {
    super.initState();
    _loadSections();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
            _scrollController.position.maxScrollExtent - 200 &&
        _hasMore &&
        !_loading) {
      _loadMore();
    }
  }

  /// Rebuild the flat photo list from sections (for PhotoPreviewScreen)
  void _rebuildFlatList() {
    _allPhotos = _sections.expand((section) => section.photos.map((sp) => Photo(
      id: sp.path,
      name: sp.filename,
      path: sp.path,
      size: 0,
      date: section.month,
      type: sp.isVideo ? 'video' : 'photo',
    ))).toList();
  }

  Future<void> _loadSections() async {
    setState(() => _loading = true);
    try {
      final data = await widget.api.getPhotoSections(page: 1);
      _availableMonths = List<String>.from(data['available_months'] ?? []);
      final sections = (data['sections'] as List? ?? [])
          .map((s) => PhotoSection.fromJson(s as Map<String, dynamic>))
          .toList();
      setState(() {
        _sections = sections;
        _hasMore = data['has_more'] ?? false;
        _page = 1;
        _loading = false;
        if (sections.isNotEmpty) {
          _displayMonth = sections.first.display;
        }
        _rebuildFlatList();
      });
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('加载失败: $e')),
        );
      }
    }
  }

  Future<void> _loadMore() async {
    if (!_hasMore || _loading) return;
    setState(() => _loading = true);
    try {
      final data = await widget.api.getPhotoSections(page: _page + 1);
      final sections = (data['sections'] as List? ?? [])
          .map((s) => PhotoSection.fromJson(s as Map<String, dynamic>))
          .toList();
      setState(() {
        _sections.addAll(sections);
        _hasMore = data['has_more'] ?? false;
        _page += 1;
        _loading = false;
        _rebuildFlatList();
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  void _jumpToSection(String month) {
    int sectionIndex = -1;
    for (int i = 0; i < _sections.length; i++) {
      if (_sections[i].month == month) {
        sectionIndex = i;
        break;
      }
    }
    if (sectionIndex >= 0) {
      final offset = _estimateSectionOffset(sectionIndex, _isTablet);
      _scrollController.animateTo(
        offset,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
      setState(() => _displayMonth = _sections[sectionIndex].display);
    }
  }

  void _jumpToMonth(int year, int month) {
    final target = '$year-${month.toString().padLeft(2, '0')}';
    _jumpToSection(target);
  }

  double _estimateSectionOffset(int sectionIndex, bool isTablet) {
    double offset = 0;
    offset += 56; // toolbar height
    final cols = isTablet ? _gridColumns : 3;
    for (int i = 0; i < sectionIndex; i++) {
      final photos = _sections[i].photos.length;
      final rows = (photos / cols).ceil();
      offset += 44; // header
      offset += rows * 130; // row height
    }
    return offset;
  }

  void _showDatePicker() {
    MonthCalendarSheet.show(
      context,
      availableMonths: _availableMonths,
      selectedMonth: _displayMonth.isNotEmpty
          ? _displayMonth.replaceAll('年', '-').replaceAll('月', '')
          : null,
      onSelect: _jumpToMonth,
    );
  }

  void _openFolderView() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => FolderScreen(api: widget.api),
      ),
    );
  }

  void _openPhoto(int sectionIndex, int photoIndex) {
    // Find global index from pre-built flat list
    int globalIndex = 0;
    for (int si = 0; si < sectionIndex; si++) {
      globalIndex += _sections[si].photos.length;
    }
    globalIndex += photoIndex;

    if (globalIndex >= _allPhotos.length) return;

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => PhotoPreviewScreen(
          api: widget.api,
          photos: _allPhotos,
          initialIndex: globalIndex,
        ),
      ),
    );
  }

  bool get _isTablet => MediaQuery.of(context).size.width > 600;

  @override
  Widget build(BuildContext context) {
    if (_isTablet) {
      return _buildTabletLayout();
    }
    return _buildMobileLayout();
  }

  // ===== Mobile Layout =====
  Widget _buildMobileLayout() {
    final theme = Theme.of(context);
    return Column(
      children: [
        _buildAlbumToolbar(theme),
        Expanded(child: _buildPhotoGrid()),
      ],
    );
  }

  Widget _buildAlbumToolbar(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton.icon(
              onPressed: _showDatePicker,
              icon: const Icon(Icons.calendar_today, size: 16),
              label: Text(_displayMonth.isNotEmpty ? _displayMonth : '选择月份'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                side: BorderSide(color: theme.dividerColor),
              ),
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 44,
            height: 44,
            child: OutlinedButton(
              onPressed: _openFolderView,
              style: OutlinedButton.styleFrom(
                padding: EdgeInsets.zero,
                side: BorderSide(color: theme.dividerColor),
              ),
              child: const Icon(Icons.folder, size: 20),
            ),
          ),
        ],
      ),
    );
  }

  // ===== Tablet Layout =====
  Widget _buildTabletLayout() {
    final theme = Theme.of(context);
    return Row(
      children: [
        if (!_sidebarCollapsed)
          TabletSidebar(
            sections: _sections,
            activeSection: _displayMonth.replaceAll('年', '-').replaceAll('月', ''),
            onSelectSection: _jumpToSection,
            onCollapse: () => setState(() => _sidebarCollapsed = true),
          ),
        if (_sidebarCollapsed)
          TabletSidebarExpandButton(
            onTap: () => setState(() => _sidebarCollapsed = false),
          ),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Toolbar row (logo is in shared AppBar)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _showDatePicker,
                        icon: const Icon(Icons.calendar_today, size: 16),
                        label: Text(
                          _displayMonth.isNotEmpty ? _displayMonth : '跳转月份',
                        ),
                        style: OutlinedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          side: BorderSide(color: theme.dividerColor),
                          visualDensity: VisualDensity.compact,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: _buildPhotoGrid(isTablet: true),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ===== Photo Grid (shared) =====
  Widget _buildPhotoGrid({bool isTablet = false}) {
    final columns = isTablet ? _gridColumns : 3;

    return _loading && _sections.isEmpty
        ? const Center(child: CircularProgressIndicator())
        : RefreshIndicator(
            onRefresh: _loadSections,
            child: GestureDetector(
              onScaleStart: isTablet ? _handlePinchStart : null,
              onScaleUpdate: isTablet ? _handlePinchZoom : null,
              child: CustomScrollView(
                controller: _scrollController,
                slivers: [
                  for (var si = 0; si < _sections.length; si++) ...[
                    SliverToBoxAdapter(
                      child: Padding(
                        padding:
                            const EdgeInsets.fromLTRB(16, 16, 16, 8),
                        child: Row(
                          children: [
                            Text(
                              _sections[si].display,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              '(${_sections[si].count})',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall,
                            ),
                          ],
                        ),
                      ),
                    ),
                    SliverGrid(
                      gridDelegate:
                          SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: columns,
                        crossAxisSpacing: 2,
                        mainAxisSpacing: 2,
                        childAspectRatio: 1,
                      ),
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final sectionIndex = si;
                          final photo = _sections[sectionIndex]
                              .photos[index];
                          return _PhotoGridItem(
                            photo: photo,
                            api: widget.api,
                            onTap: () =>
                                _openPhoto(sectionIndex, index),
                          );
                        },
                        childCount: _sections[si].photos.length,
                      ),
                    ),
                  ],
                  if (_loading && _sections.isNotEmpty)
                    const SliverToBoxAdapter(
                      child: Center(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: CircularProgressIndicator(
                              strokeWidth: 2),
                        ),
                      ),
                    ),
                  const SliverToBoxAdapter(
                    child: SizedBox(height: 80),
                  ),
                ],
              ),
            ),
          );
  }

  /// 双指缩放：调整网格列数
  void _handlePinchStart(ScaleStartDetails details) {
    _pinchStartScale = 1.0;
    _pinchTriggered = false;
  }

  /// 双指缩放：调整网格列数
  void _handlePinchZoom(ScaleUpdateDetails details) {
    if (_pinchTriggered) return; // 每次手势只触发一次
    final delta = details.scale - _pinchStartScale;
    if (delta < -0.3) {
      // Zoom out → more columns
      setState(() => _gridColumns = (_gridColumns + 1).clamp(3, 8));
      _pinchTriggered = true;
    } else if (delta > 0.3) {
      // Zoom in → fewer columns
      setState(() => _gridColumns = (_gridColumns - 1).clamp(3, 8));
      _pinchTriggered = true;
    }
  }
}

/// 网格中的照片项
class _PhotoGridItem extends StatelessWidget {
  final SectionPhoto photo;
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
                    Icon(Icons.play_arrow,
                        size: 12, color: Colors.white),
                    SizedBox(width: 2),
                    Text('视频',
                        style: TextStyle(
                            fontSize: 10, color: Colors.white)),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
