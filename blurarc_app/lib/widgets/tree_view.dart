import 'package:flutter/material.dart';
import '../models/album_tree.dart';

class TreeView extends StatefulWidget {
  final List<TreeNode> nodes;
  final void Function(String path) onSelect;

  const TreeView({super.key, required this.nodes, required this.onSelect});

  @override
  State<TreeView> createState() => _TreeViewState();
}

class _TreeViewState extends State<TreeView> {
  final Set<String> _expandedPaths = {};

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      children: widget.nodes.map((node) => _buildNode(node, 0)).toList(),
    );
  }

  Widget _buildNode(TreeNode node, int depth) {
    final hasChildren = node.children.isNotEmpty;
    final isExpanded = _expandedPaths.contains(node.path);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        InkWell(
          onTap: () {
            if (hasChildren) {
              setState(() {
                if (isExpanded) {
                  _expandedPaths.remove(node.path);
                } else {
                  _expandedPaths.add(node.path);
                }
              });
            } else {
              widget.onSelect(node.path);
            }
          },
          child: Padding(
            padding: EdgeInsets.only(left: depth * 16.0 + 12),
            child: Row(
              children: [
                if (hasChildren)
                  Icon(
                    isExpanded ? Icons.expand_more : Icons.chevron_right,
                    size: 20,
                    color: Colors.grey,
                  )
                else
                  const SizedBox(width: 20),
                const SizedBox(width: 8),
                Icon(
                  node.isYear ? Icons.calendar_today : Icons.folder,
                  size: 16,
                  color: node.isYearMonth
                      ? const Color(0xFF22D3EE)
                      : Colors.grey,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    node.name,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight:
                          node.isYear ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                ),
                if (node.count > 0)
                  Text(
                    '${node.count}',
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
              ],
            ),
          ),
        ),
        if (hasChildren && isExpanded)
          ...node.children.map((child) => _buildNode(child, depth + 1)),
      ],
    );
  }
}
