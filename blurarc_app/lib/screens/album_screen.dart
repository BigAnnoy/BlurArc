import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../models/album_tree.dart';
import '../widgets/tree_view.dart';
import '../widgets/responsive_layout.dart';
import 'photo_grid_screen.dart';

class AlbumScreen extends StatefulWidget {
  final ApiClient api;

  const AlbumScreen({super.key, required this.api});

  @override
  State<AlbumScreen> createState() => _AlbumScreenState();
}

class _AlbumScreenState extends State<AlbumScreen> {
  List<TreeNode> _treeNodes = [];
  String? _selectedPath;
  int _totalPhotos = 0;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadTree();
  }

  Future<void> _loadTree() async {
    setState(() => _loading = true);
    try {
      final data = await widget.api.getTree();
      final children = (data['children'] as List? ?? [])
          .map((c) => TreeNode.fromJson(c as Map<String, dynamic>))
          .toList();

      final stats = await widget.api.getStats();
      _totalPhotos = stats['total_files'] ?? 0;

      setState(() {
        _treeNodes = children;
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

  void _onSelectPath(String path) {
    setState(() => _selectedPath = path);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_selectedPath != null
            ? _selectedPath!.split('/').last
            : 'Blur Arc 相册'),
        actions: [
          IconButton(
            icon: const Icon(Icons.upload_file),
            onPressed: () {
              Navigator.pushNamed(context, '/upload');
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await widget.api.disconnect();
              if (!mounted) return;
              // ignore: use_build_context_synchronously
              Navigator.pushReplacementNamed(context, '/');
            },
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ResponsiveLayout(
              mobile: _buildMobileLayout(),
              tablet: _buildTabletLayout(),
            ),
    );
  }

  Widget _buildMobileLayout() {
    if (_selectedPath == null) {
      // Show tree view
      return TreeView(
        nodes: _treeNodes,
        onSelect: (path) {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => PhotoGridScreen(
                path: path,
                api: widget.api,
              ),
            ),
          ).then((_) {
            // Reset selected path when returning
            setState(() => _selectedPath = null);
          });
        },
      );
    }
    return PhotoGridScreen(
      path: _selectedPath!,
      api: widget.api,
    );
  }

  Widget _buildTabletLayout() {
    return Row(
      children: [
        SizedBox(
          width: 280,
          child: Card(
            margin: EdgeInsets.zero,
            shape: const RoundedRectangleBorder(),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      const Icon(Icons.photo_library,
                          color: Color(0xFF22D3EE)),
                      const SizedBox(width: 8),
                      Text('相册 · $_totalPhotos 张',
                          style: const TextStyle(
                              fontSize: 16, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                const Divider(height: 1),
                Expanded(
                  child: TreeView(
                    nodes: _treeNodes,
                    onSelect: _onSelectPath,
                  ),
                ),
              ],
            ),
          ),
        ),
        const VerticalDivider(width: 1),
        Expanded(
          child: _selectedPath != null
              ? PhotoGridScreen(
                  path: _selectedPath!,
                  api: widget.api,
                )
              : const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.folder_open, size: 64, color: Colors.grey),
                      SizedBox(height: 16),
                      Text('选择一个文件夹浏览照片',
                          style: TextStyle(color: Colors.grey)),
                    ],
                  ),
                ),
        ),
      ],
    );
  }
}
