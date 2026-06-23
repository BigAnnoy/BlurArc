/// 文件夹视图 — 按目录结构浏览照片
library;

import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../models/folder_entry.dart';

class FolderScreen extends StatefulWidget {
  final ApiClient api;

  const FolderScreen({super.key, required this.api});

  @override
  State<FolderScreen> createState() => _FolderScreenState();
}

class _FolderScreenState extends State<FolderScreen> {
  List<FolderEntry> _folders = [];
  List<BreadcrumbNode> _breadcrumb = [];
  String _currentPath = '';
  String? _parentPath;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadFolder();
  }

  Future<void> _loadFolder({String? path}) async {
    setState(() => _loading = true);
    try {
      final data = await widget.api.getFolders(path: path);
      _folders = (data['folders'] as List? ?? [])
          .map((f) => FolderEntry.fromJson(f as Map<String, dynamic>))
          .toList();
      _breadcrumb = (data['breadcrumb'] as List? ?? [])
          .map((b) => BreadcrumbNode.fromJson(b as Map<String, dynamic>))
          .toList();
      _currentPath = data['current_path'] ?? '';
      _parentPath = data['parent_path'];
      setState(() => _loading = false);
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('加载失败: $e')),
        );
      }
    }
  }

  void _onTapFolder(FolderEntry folder) {
    _loadFolder(path: folder.path);
  }

  void _onTapBreadcrumb(int index) {
    if (index < _breadcrumb.length) {
      _loadFolder(path: _breadcrumb[index].path);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isTablet = MediaQuery.of(context).size.width > 600;

    return Scaffold(
      // 原型 mobile：无 AppBar，顶部只有 `‹ 返回相册` 文本按钮
      // 原型 tablet：保留 AppBar（带路径标题）
      appBar: isTablet
          ? AppBar(
              title: Text(_currentPath.isNotEmpty
                  ? _currentPath.split('/').last
                  : '文件夹'),
            )
          : null,
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // mobile: 顶部返回按钮；tablet: 跳过（已由 AppBar 提供）
                if (!isTablet)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: InkWell(
                      onTap: () => Navigator.of(context).pop(),
                      child: const Padding(
                        padding: EdgeInsets.fromLTRB(12, 8, 12, 8),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              '‹',
                              style: TextStyle(fontSize: 20, height: 1.0),
                            ),
                            SizedBox(width: 4),
                            Text(
                              '返回相册',
                              style: TextStyle(fontSize: 15),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                // 面包屑导航
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  height: 44,
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: _breadcrumb.length,
                    itemBuilder: (context, index) {
                      final node = _breadcrumb[index];
                      final isLast = index == _breadcrumb.length - 1;
                      return GestureDetector(
                        onTap: () => _onTapBreadcrumb(index),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              node.name,
                              style: TextStyle(
                                fontSize: 13,
                                color: isLast
                                    ? theme.textTheme.bodyLarge?.color
                                    : theme.colorScheme.primary,
                                fontWeight: isLast
                                    ? FontWeight.w600
                                    : FontWeight.normal,
                              ),
                            ),
                            if (!isLast)
                              Padding(
                                padding:
                                    const EdgeInsets.symmetric(horizontal: 4),
                                child: Icon(
                                  Icons.chevron_right,
                                  size: 16,
                                  color: theme.colorScheme.onSurface
                                      .withAlpha(100),
                                ),
                              ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
                const Divider(height: 1),
                // 返回上级 — 原型：folder-back-btn 样式
                if (_parentPath != null)
                  InkWell(
                    onTap: () => _loadFolder(path: _parentPath),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 8),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            '‹',
                            style: TextStyle(
                              fontSize: 20,
                              color: theme.colorScheme.onSurface.withAlpha(180),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            '返回上级',
                            style: TextStyle(
                              fontSize: 13,
                              color: theme.colorScheme.onSurface.withAlpha(180),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                // 文件夹列表 — 原型：folder-item 包含 icon(20px) + name + count
                Expanded(
                  child: _folders.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.folder_off,
                                size: 48,
                                color:
                                    theme.colorScheme.onSurface.withAlpha(80),
                              ),
                              const SizedBox(height: 12),
                              Text('此文件夹为空',
                                  style: TextStyle(
                                    color: theme.colorScheme.onSurface
                                        .withAlpha(120),
                                  )),
                            ],
                          ),
                        )
                      : ListView.builder(
                          itemCount: _folders.length,
                          itemBuilder: (context, index) {
                            final folder = _folders[index];
                            return InkWell(
                              onTap: () => _onTapFolder(folder),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 10),
                                child: Row(
                                  children: [
                                    // 原型：📁 emoji，20px，宽度 24px
                                    const SizedBox(
                                      width: 24,
                                      child: Text(
                                        '📁',
                                        style: TextStyle(fontSize: 20),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(
                                        folder.name,
                                        style: const TextStyle(fontSize: 14),
                                      ),
                                    ),
                                    Text(
                                      '${folder.photoCount}',
                                      style: TextStyle(
                                        fontSize: 11,
                                        color: theme.colorScheme.onSurface
                                            .withAlpha(120),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }
}
