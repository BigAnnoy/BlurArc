class TreeNode {
  final String name;
  final String path;
  final int count;
  final List<TreeNode> children;

  TreeNode({
    required this.name,
    required this.path,
    this.count = 0,
    this.children = const [],
  });

  factory TreeNode.fromJson(Map<String, dynamic> json) => TreeNode(
        name: json['name'] ?? '',
        path: json['path'] ?? '',
        count: json['count'] ?? 0,
        children: (json['children'] as List? ?? [])
            .map((c) => TreeNode.fromJson(c as Map<String, dynamic>))
            .toList(),
      );

  bool get isYearMonth => name.length == 7 && name.contains('-');
  bool get isYear => name.length == 4 && !name.contains('-');
}
