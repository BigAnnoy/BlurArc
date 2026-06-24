/// 共享的 mock API 响应数据
///
/// 集中管理后端接口的 JSON 响应字符串，让多个 service / page 测试
/// 复用一致的 fixture。
library;

class MockResponses {
  // ===== 照片列表（/api/mobile/photos） =====

  static const String photoListJson = '''
{
  "photos": [
    {
      "id": 1,
      "name": "test_01.jpg",
      "path": "/album/2024/2024-01/test_01.jpg",
      "size": 1024000,
      "date": "2024-01-15T10:30:00",
      "type": "photo"
    },
    {
      "id": 2,
      "name": "test_02.jpg",
      "path": "/album/2024/2024-01/test_02.jpg",
      "size": 2048000,
      "date": "2024-01-16T11:00:00",
      "type": "photo"
    }
  ],
  "total": 2
}
''';

  static const String emptyPhotoListJson = '''
{
  "photos": [],
  "total": 0
}
''';

  // ===== 配对流程 =====

  /// POST /api/mobile/pair-request 成功（带 token）
  static const String pairRequestSuccessJson = '''
{
  "status": "paired",
  "token": "test_token_abc123",
  "device_id": 1
}
''';

  /// POST /api/mobile/pair-request 失败（无效配对码）
  static const String pairRequestFailJson = '''
{
  "status": "error",
  "error": "Invalid pairing code"
}
''';

  /// GET /api/mobile/pairing/pending 等待中
  static const String pairingPendingJson = '''
{
  "status": "pending"
}
''';

  /// GET /api/mobile/pairing/pending 已被 PC 确认
  static const String pairingConfirmedJson = '''
{
  "status": "confirmed"
}
''';

  /// GET /api/mobile/pairing/pending 已被 PC 拒绝
  static const String pairingRejectedJson = '''
{
  "status": "rejected"
}
''';

  /// GET /api/mobile/pairing/pending 无配对请求
  static const String pairingNoneJson = '''
{
  "status": "none"
}
''';

  // ===== 验证 token =====

  /// GET /api/mobile/verify 成功
  static const String verifySuccessJson = '''
{
  "status": "valid"
}
''';

  // ===== mDNS 发现结果（mock 用，结构与 DiscoveredService 对应） =====

  static const String serviceListJson = '''
[
  {
    "name": "BlurArc-MacBook.local",
    "host": "192.168.1.100",
    "port": 8900
  }
]
''';

  // ===== 上传响应 =====

  /// POST /api/mobile/upload 成功
  static const String uploadSuccessJson = '''
{
  "success": true,
  "uploaded": 1,
  "filename": "uploaded.jpg"
}
''';

  // ===== 错误响应 =====

  static const String internalServerErrorJson = '''
{
  "error": "Internal Server Error"
}
''';

  // ===== 树结构 / stats（settings/album） =====

  static const String treeJson = '''
{
  "root": "2024",
  "children": [
    {
      "name": "2024-01",
      "path": "2024/2024-01",
      "photo_count": 2
    },
    {
      "name": "2024-02",
      "path": "2024/2024-02",
      "photo_count": 0
    }
  ]
}
''';

  static const String statsJson = '''
{
  "total_photos": 1234,
  "total_videos": 12,
  "total_size": 5678901234
}
''';
}
