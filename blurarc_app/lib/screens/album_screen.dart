/// 相册页面（手机/平板）
/// 显示月份列表 → 点击某月 → 跳转 MonthPhotoScreen 加载该月照片
library;

import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../models/photo_section.dart';
import '../widgets/tablet_sidebar.dart';
import 'folder_screen.dart';
import 'month_photo_screen.dart';

class AlbumScreen extends StatefulWidget {
  final ApiClient api;

  const AlbumScreen({super.key, required this.api});

  @override
  State<AlbumScreen> createState() => _AlbumScreenState();
}

class _AlbumScreenState extends State<AlbumScreen> {
  List<PhotoSection> _sections = [];
  bool _loading = true;
  bool _hasMore = true;
  int _page = 1;
  final _scrollController = ScrollController();

  // Tablet state
  bool _sidebarCollapsed = false;

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

  Future<void> _loadSections() async {
    setState(() => _loading = true);
    try {
      final data = await widget.api.getPhotoSections(page: 1);
      final sections = (data['sections'] as List? ?? [])
          .map((s) => PhotoSection.fromJson(s as Map<String, dynamic>))
          .toList();
      setState(() {
        _sections = sections;
        _hasMore = data['has_more'] ?? false;
        _page = 1;
        _loading = false;
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
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  void _openMonth(PhotoSection section) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => MonthPhotoScreen(
          api: widget.api,
          month: section.month,
          displayName: section.display,
        ),
      ),
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
    return Column(
      children: [
        _buildAlbumToolbar(),
        Expanded(child: _buildMonthList()),
      ],
    );
  }

  Widget _buildAlbumToolbar() {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        children: [
          const Text('相册',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          const Spacer(),
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

  // ===== Month List =====
  Widget _buildMonthList() {
    if (_loading && _sections.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_sections.isEmpty) {
      return const Center(child: Text('暂无照片'));
    }
    return RefreshIndicator(
      onRefresh: _loadSections,
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        itemCount: _sections.length + (_hasMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index >= _sections.length) {
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            );
          }
          final section = _sections[index];
          return Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor:
                    Theme.of(context).colorScheme.primary.withAlpha(30),
                child: Icon(Icons.photo_library,
                    color: Theme.of(context).colorScheme.primary),
              ),
              title: Text(section.display,
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text('${section.count} 张照片'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => _openMonth(section),
            ),
          );
        },
      ),
    );
  }

  // ===== Tablet Layout =====
  Widget _buildTabletLayout() {
    return Row(
      children: [
        if (!_sidebarCollapsed)
          TabletSidebar(
            sections: _sections,
            activeSection: '',
            onSelectSection: (month) {
              final found = _sections.where((s) => s.month == month);
              if (found.isNotEmpty) _openMonth(found.first);
            },
            onCollapse: () => setState(() => _sidebarCollapsed = true),
          ),
        if (_sidebarCollapsed)
          TabletSidebarExpandButton(
            onTap: () => setState(() => _sidebarCollapsed = false),
          ),
        Expanded(child: _buildMonthList()),
      ],
    );
  }
}
