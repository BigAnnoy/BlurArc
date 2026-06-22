/// 相册页面（手机/平板）
///
/// 设计（与原型图一致）：
/// - 主区域是连续滚动的照片网格
/// - 按月分组，每组前有 section header（如 "2026年6月"）
/// - 工具栏带"📅 跳转月份 ▼"按钮
/// - 平板：5列网格 + 侧栏
/// - 手机：3列网格
library;

import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../services/api_client.dart';
import '../models/photo.dart';
import '../models/photo_section_with_photos.dart';
import '../widgets/tablet_sidebar.dart';
import '../widgets/month_calendar_sheet.dart';
import 'photo_preview_screen.dart';
import 'folder_screen.dart';

class AlbumScreen extends StatefulWidget {
  final ApiClient api;

  const AlbumScreen({super.key, required this.api});

  @override
  State<AlbumScreen> createState() => _AlbumScreenState();
}

class _AlbumScreenState extends State<AlbumScreen> {
  // 连续网格数据
  final List<PhotoSectionWithPhotos> _sections = [];
  // 侧栏用的精简 section（仅元数据）
  List<_SectionMeta> _sidebarMetas = [];
  bool _loading = true;
  bool _loadingMore = false;
  bool _hasMore = true;
  int _page = 1;
  String? _loadError;
  List<String> _availableMonths = [];
  String? _activeMonth; // 当前激活（滚动到的）月份

  final _scrollController = ScrollController();
  final Map<String, GlobalKey> _sectionKeys = {};

  // Tablet state
  bool _sidebarCollapsed = false;

  static const int _pageSize = 6; // 每页几个月
  static const int _photosPerSection = 60;

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
        !_loadingMore &&
        !_loading) {
      _loadMore();
    }
    _updateActiveMonth();
  }

  void _updateActiveMonth() {
    if (_sections.isEmpty) return;
    // 找到当前 viewport 顶部最近且 >= 顶部位置的 section
    final renderBox = context.findRenderObject() as RenderBox?;
    if (renderBox == null) return;
    final viewportTop = renderBox.localToGlobal(Offset.zero).dy;
    String? newActive;
    for (final meta in _sidebarMetas) {
      final key = _sectionKeys[meta.month];
      if (key == null) continue;
      final ctx = key.currentContext;
      if (ctx == null) continue;
      final box = ctx.findRenderObject() as RenderBox?;
      if (box == null) continue;
      final pos = box.localToGlobal(Offset.zero).dy;
      if (pos <= viewportTop + 60) {
        newActive = meta.month;
      } else {
        break;
      }
    }
    if (newActive != null && newActive != _activeMonth) {
      setState(() => _activeMonth = newActive);
    }
  }

  Future<void> _loadSections() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final data = await widget.api.getAllPhotosBySection(
        page: 1,
        pageSize: _pageSize,
        photosPerSection: _photosPerSection,
      );
      final sections = (data['sections'] as List? ?? [])
          .map(
              (s) => PhotoSectionWithPhotos.fromJson(s as Map<String, dynamic>))
          .toList();
      final months = (data['available_months'] as List? ?? [])
          .map((e) => e.toString())
          .toList();
      setState(() {
        _sections
          ..clear()
          ..addAll(sections);
        _sidebarMetas = sections
            .map((s) => _SectionMeta(s.month, s.display, s.count))
            .toList();
        _availableMonths = months;
        _hasMore = data['has_more'] ?? false;
        _page = 1;
        _loading = false;
        _activeMonth = sections.isNotEmpty ? sections.first.month : null;
        _ensureKeys();
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _loadError = e.toString();
      });
    }
  }

  Future<void> _loadMore() async {
    if (!_hasMore || _loadingMore) return;
    setState(() => _loadingMore = true);
    try {
      final data = await widget.api.getAllPhotosBySection(
        page: _page + 1,
        pageSize: _pageSize,
        photosPerSection: _photosPerSection,
      );
      final sections = (data['sections'] as List? ?? [])
          .map(
              (s) => PhotoSectionWithPhotos.fromJson(s as Map<String, dynamic>))
          .toList();
      setState(() {
        _sections.addAll(sections);
        _sidebarMetas.addAll(sections
            .map((s) => _SectionMeta(s.month, s.display, s.count))
            .toList());
        _hasMore = data['has_more'] ?? false;
        _page += 1;
        _loadingMore = false;
        _ensureKeys();
      });
    } catch (_) {
      setState(() => _loadingMore = false);
    }
  }

  void _ensureKeys() {
    for (final s in _sections) {
      _sectionKeys.putIfAbsent(s.month, () => GlobalKey());
    }
  }

  void _scrollToMonth(String month) {
    final key = _sectionKeys[month];
    if (key?.currentContext != null) {
      Scrollable.ensureVisible(
        key!.currentContext!,
        duration: const Duration(milliseconds: 320),
        curve: Curves.easeInOut,
        alignment: 0.0,
      );
    }
  }

  void _openFolderView() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => FolderScreen(api: widget.api)),
    );
  }

  void _openPhoto(PhotoItem photo) {
    // 将单张照片包装为 List<Photo> 供 PhotoPreviewScreen 使用
    final photoModel = Photo(
      id: photo.path,
      name: photo.filename,
      path: photo.path,
      size: 0,
      date: photo.mediaDate ?? '',
      type: photo.isVideo ? 'video' : 'photo',
    );
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => PhotoPreviewScreen(
          api: widget.api,
          photos: [photoModel],
          initialIndex: 0,
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
    return Column(
      children: [
        _buildAlbumToolbar(),
        Expanded(child: _buildContent()),
      ],
    );
  }

  Widget _buildAlbumToolbar() {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: theme.dividerColor, width: 0.5),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: _OutlineButton(
              emoji: '📅',
              label: _activeMonthDisplay(),
              onTap: _showDatePanel,
              showDropdownArrow: true,
            ),
          ),
          const SizedBox(width: 8),
          _IconButton(
            icon: Icons.folder,
            onTap: _openFolderView,
          ),
        ],
      ),
    );
  }

  String _activeMonthDisplay() {
    if (_activeMonth == null) return '跳转月份';
    final m = _activeMonth!;
    if (m == 'no-date') return '未知日期';
    return _formatMonth(m);
  }

  String _formatMonth(String m) {
    try {
      final parts = m.split('-');
      return '${parts[0]}年${int.parse(parts[1])}月';
    } catch (_) {
      return m;
    }
  }

  // ===== Tablet Layout =====
  Widget _buildTabletLayout() {
    return Row(
      children: [
        if (!_sidebarCollapsed)
          TabletSidebar(
            sections: _sidebarMetas,
            activeSection: _activeMonth,
            onSelectSection: (month) => _scrollToMonth(month),
            onCollapse: () => setState(() => _sidebarCollapsed = true),
          ),
        if (_sidebarCollapsed)
          TabletSidebarExpandButton(
            onTap: () => setState(() => _sidebarCollapsed = false),
          ),
        Expanded(
          child: Column(
            children: [
              _buildTabletToolbar(),
              Expanded(child: _buildContent()),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTabletToolbar() {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      decoration: BoxDecoration(
        color: theme.appBarTheme.backgroundColor,
        border: Border(
          bottom: BorderSide(color: theme.dividerColor, width: 0.5),
        ),
      ),
      child: Row(
        children: [
          Text(
            _activeMonthDisplay(),
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: theme.colorScheme.onSurface,
            ),
          ),
          const Spacer(),
          _OutlineButton(
            emoji: '📅',
            label: '跳转月份',
            onTap: _showDatePanel,
            showDropdownArrow: true,
          ),
        ],
      ),
    );
  }

  void _showDatePanel() {
    if (_availableMonths.isEmpty) return;
    if (_isTablet) {
      // 平板：弹一个居中浮层
      showDialog(
        context: context,
        barrierColor: Colors.black26,
        builder: (_) => _TabletDatePanel(
          availableMonths: _availableMonths,
          selectedMonth: _activeMonth,
          onSelect: (year, month) {
            Navigator.pop(context);
            _scrollToMonth('$year-${month.toString().padLeft(2, '0')}');
          },
        ),
      );
    } else {
      // 手机：底部弹层
      MonthCalendarSheet.show(
        context,
        availableMonths: _availableMonths,
        selectedMonth: _activeMonth,
        onSelect: (year, month) {
          _scrollToMonth('$year-${month.toString().padLeft(2, '0')}');
        },
      );
    }
  }

  // ===== Content (continuous grid) =====
  Widget _buildContent() {
    if (_loading && _sections.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_loadError != null && _sections.isEmpty) {
      return _buildErrorView(_loadError!, _loadSections);
    }
    if (_sections.isEmpty) {
      return const Center(child: Text('暂无照片'));
    }
    final cols = _isTablet ? 5 : 3;
    final hPad = _isTablet ? 4.0 : 4.0;
    final gap = _isTablet ? 3.0 : 2.0;
    return RefreshIndicator(
      onRefresh: _loadSections,
      child: ListView.builder(
        controller: _scrollController,
        padding: EdgeInsets.zero,
        itemCount: _sections.length + (_hasMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index >= _sections.length) {
            return const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            );
          }
          final section = _sections[index];
          return _SectionBlock(
            key: _sectionKeys[section.month],
            section: section,
            cols: cols,
            hPad: hPad,
            gap: gap,
            isTablet: _isTablet,
            onPhotoTap: _openPhoto,
            api: widget.api,
          );
        },
      ),
    );
  }

  // ===== Error View =====
  Widget _buildErrorView(String error, VoidCallback onRetry) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline,
                size: 48, color: Theme.of(context).colorScheme.error),
            const SizedBox(height: 12),
            const Text('加载失败',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Text(
              _formatErrorMessage(error),
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 13, color: Colors.grey),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('重试'),
            ),
          ],
        ),
      ),
    );
  }

  String _formatErrorMessage(String raw) {
    if (raw.contains('TimeoutException') || raw.contains('timeout')) {
      return '网络请求超时，请检查 PC 端是否正常';
    }
    if (raw.contains('SocketException') || raw.contains('Connection')) {
      return '无法连接到 PC，请检查网络';
    }
    return raw.length > 100 ? '${raw.substring(0, 100)}...' : raw;
  }
}

// ===== Section Meta (for sidebar) =====
class _SectionMeta {
  final String month;
  final String display;
  final int count;
  _SectionMeta(this.month, this.display, this.count);
}

// ===== Section Block (month header + grid) =====
class _SectionBlock extends StatelessWidget {
  final PhotoSectionWithPhotos section;
  final int cols;
  final double hPad;
  final double gap;
  final bool isTablet;
  final void Function(PhotoItem) onPhotoTap;
  final ApiClient api;

  const _SectionBlock({
    super.key,
    required this.section,
    required this.cols,
    required this.hPad,
    required this.gap,
    required this.isTablet,
    required this.onPhotoTap,
    required this.api,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // 原型差异：mobile padding 14×12×8, 13px; tablet padding 16×16×8, 14px
    final headerH = isTablet ? 16.0 : 14.0;
    final headerSide = isTablet ? 16.0 : 12.0;
    final headerFontSize = isTablet ? 14.0 : 13.0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header
        Padding(
          padding: EdgeInsets.fromLTRB(
            isTablet ? hPad + headerSide : headerSide,
            headerH,
            isTablet ? hPad + headerSide : headerSide,
            8,
          ),
          child: Text(
            section.display,
            style: TextStyle(
              fontSize: headerFontSize,
              color: theme.textTheme.bodyMedium?.color ??
                  theme.colorScheme.onSurface.withAlpha(180),
              fontWeight: FontWeight.w500,
              letterSpacing: 0.2,
            ),
          ),
        ),
        // Photo grid
        Padding(
          padding: EdgeInsets.symmetric(horizontal: hPad),
          child: GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: section.photos.length,
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: cols,
              mainAxisSpacing: gap,
              crossAxisSpacing: gap,
              childAspectRatio: 1,
            ),
            itemBuilder: (context, index) {
              final p = section.photos[index];
              return _PhotoCell(
                photo: p,
                api: api,
                onTap: () => onPhotoTap(p),
              );
            },
          ),
        ),
      ],
    );
  }
}

// ===== Photo Cell =====
class _PhotoCell extends StatelessWidget {
  final PhotoItem photo;
  final ApiClient api;
  final VoidCallback onTap;

  const _PhotoCell({
    required this.photo,
    required this.api,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: theme.cardTheme.color ?? theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(3),
          boxShadow: theme.brightness == Brightness.light
              ? [
                  BoxShadow(
                    color: Colors.black.withAlpha(8),
                    blurRadius: 2,
                    offset: const Offset(0, 1),
                  ),
                ]
              : null,
        ),
        clipBehavior: Clip.antiAlias,
        child: Stack(
          fit: StackFit.expand,
          children: [
            CachedNetworkImage(
              imageUrl: _resolveThumbUrl(photo.thumbnail),
              fit: BoxFit.cover,
              placeholder: (_, __) => Container(
                color: theme.dividerColor,
              ),
              errorWidget: (_, __, ___) => Container(
                color: theme.dividerColor,
                child: Icon(Icons.broken_image,
                    size: 22, color: theme.colorScheme.onSurface.withAlpha(80)),
              ),
            ),
            if (photo.isVideo)
              const Positioned(
                bottom: 3,
                right: 3,
                child: Icon(
                  Icons.play_circle_fill,
                  color: Colors.white70,
                  size: 20,
                ),
              ),
          ],
        ),
      ),
    );
  }

  String _resolveThumbUrl(String thumbnail) {
    if (thumbnail.isEmpty) return '';
    // 后端返回的是相对路径 '/api/mobile/thumbnail?path=...'，需要拼上 baseUrl
    String url;
    if (thumbnail.startsWith('http')) {
      url = thumbnail;
    } else {
      url = '${api.baseUrl}$thumbnail';
    }
    // CachedNetworkImage 不走 Dio 拦截器，Authorization 不会自动加；
    // 后端 mobile_access_server._extract_token 支持从 query 兜底读取 token
    if (api.token != null && api.token!.isNotEmpty) {
      final sep = url.contains('?') ? '&' : '?';
      url = '$url${sep}token=${Uri.encodeComponent(api.token!)}';
    }
    return url;
  }
}

// ===== Reusable: outline button =====
class _OutlineButton extends StatelessWidget {
  final IconData? icon;
  final String? emoji;
  final String label;
  final VoidCallback onTap;
  final bool showDropdownArrow;

  const _OutlineButton({
    this.icon,
    this.emoji,
    required this.label,
    required this.onTap,
    this.showDropdownArrow = false,
  }) : assert(icon != null || emoji != null, 'icon 或 emoji 必须传一个');

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Material(
      color: theme.cardTheme.color ?? theme.colorScheme.surface,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: theme.dividerColor, width: 0.5),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (emoji != null)
                Text(emoji!, style: const TextStyle(fontSize: 14))
              else
                Icon(icon,
                    size: 14,
                    color: theme.colorScheme.onSurface.withAlpha(180)),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  label,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 13,
                    color: theme.colorScheme.onSurface.withAlpha(180),
                  ),
                ),
              ),
              if (showDropdownArrow) ...[
                const SizedBox(width: 4),
                Icon(Icons.arrow_drop_down,
                    size: 16,
                    color: theme.colorScheme.onSurface.withAlpha(180)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _IconButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _IconButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Material(
      color: theme.cardTheme.color ?? theme.colorScheme.surface,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: theme.dividerColor, width: 0.5),
          ),
          child: Icon(icon,
              size: 18, color: theme.colorScheme.onSurface.withAlpha(180)),
        ),
      ),
    );
  }
}

// ===== Tablet Date Panel (centered overlay) =====
class _TabletDatePanel extends StatefulWidget {
  final List<String> availableMonths;
  final String? selectedMonth;
  final void Function(int year, int month) onSelect;

  const _TabletDatePanel({
    required this.availableMonths,
    required this.selectedMonth,
    required this.onSelect,
  });

  @override
  State<_TabletDatePanel> createState() => _TabletDatePanelState();
}

class _TabletDatePanelState extends State<_TabletDatePanel> {
  late int _year;

  @override
  void initState() {
    super.initState();
    _year = DateTime.now().year;
    if (widget.selectedMonth != null && widget.selectedMonth != 'no-date') {
      _year = int.tryParse(widget.selectedMonth!.split('-')[0]) ?? _year;
    } else if (widget.availableMonths.isNotEmpty) {
      _year = int.tryParse(widget.availableMonths.first.split('-')[0]) ?? _year;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Material(
        color: Colors.transparent,
        child: Container(
          width: 360,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withAlpha(40),
                blurRadius: 32,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Year nav
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    onPressed: () => setState(() => _year--),
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Text('$_year 年', style: theme.textTheme.titleLarge),
                  IconButton(
                    onPressed: () => setState(() => _year++),
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              // Month grid
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: 12,
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 4,
                  mainAxisSpacing: 6,
                  crossAxisSpacing: 6,
                  childAspectRatio: 2.0,
                ),
                itemBuilder: (context, index) {
                  final month = index + 1;
                  final mStr = '$_year-${month.toString().padLeft(2, '0')}';
                  final has = widget.availableMonths.contains(mStr);
                  final isSel = mStr == widget.selectedMonth;
                  return _MonthTile(
                    month: month,
                    hasPhotos: has,
                    isSelected: isSel,
                    onTap: has ? () => widget.onSelect(_year, month) : null,
                  );
                },
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () => Navigator.pop(context),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    side: BorderSide(color: theme.dividerColor, width: 1),
                  ),
                  child: Text('取消',
                      style: TextStyle(color: theme.colorScheme.onSurface)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MonthTile extends StatelessWidget {
  final int month;
  final bool hasPhotos;
  final bool isSelected;
  final VoidCallback? onTap;
  const _MonthTile({
    required this.month,
    required this.hasPhotos,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primary = theme.colorScheme.primary;
    final bg = isSelected ? primary.withAlpha(20) : Colors.transparent;
    final text = !hasPhotos
        ? theme.colorScheme.onSurface.withAlpha(40)
        : isSelected
            ? primary
            : theme.colorScheme.onSurface.withAlpha(150);
    final countStyle = TextStyle(
      fontSize: 9,
      fontWeight: FontWeight.w600,
      color: hasPhotos ? primary : Colors.transparent,
    );
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(6),
          border: isSelected
              ? null
              : Border.all(color: theme.dividerColor, width: 0.5),
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Text(
              '$month月',
              style: TextStyle(
                fontSize: 13,
                color: text,
                fontWeight: hasPhotos ? FontWeight.w500 : FontWeight.normal,
              ),
            ),
            Positioned(
              bottom: 2,
              child: Text('·', style: countStyle),
            ),
          ],
        ),
      ),
    );
  }
}
