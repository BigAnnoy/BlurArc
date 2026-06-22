import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';

class ApiClient {
  static const String _tokenKey = 'mobile_token';
  static const String _hostKey = 'mobile_host';
  static const String _portKey = 'mobile_port';

  /// Android 模拟器访问主机 localhost 的特殊地址
  static const String _emulatorHost = '10.0.2.2';

  late final Dio _dio;
  String? _host;
  int? _port;
  String? _token;
  void Function()? onDisconnected;
  // 仅在已经成功建立过连接后才允许触发 onDisconnected，避免首次请求失败时误断连
  bool _everConnected = false;

  ApiClient({this.onDisconnected}) {
    _dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 5),
      // 修复：补 sendTimeout。/api/mobile/photos/sections 等接口先做 DB 查询再回 JSON，
      // 首次请求可能 >10s，没有 sendTimeout 会导致 loading 永远转。
      sendTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_token != null) {
          options.headers['Authorization'] = 'Bearer $_token';
        }
        handler.next(options);
      },
      onResponse: (response, handler) {
        // 收到任何 2xx 响应都视为已建立连接（覆盖 onError 中"曾经连接过"的判断）
        if (response.statusCode != null && response.statusCode! < 500) {
          _everConnected = true;
        }
        handler.next(response);
      },
      onError: (error, handler) {
        if (error.response?.statusCode == 401) {
          _token = null;
          _clearStored();
        } else if (_everConnected &&
            (error.type == DioExceptionType.connectionTimeout ||
                error.type == DioExceptionType.connectionError ||
                error.type == DioExceptionType.sendTimeout)) {
          // PC 端可能断开了连接（仅在曾经成功连接过的情况下触发，避免配对阶段误判）
          _everConnected = false;
          onDisconnected?.call();
        }
        handler.next(error);
      },
    ));
  }

  String? get host => _host;
  int? get port => _port;
  String? get token => _token;

  /// 解析主机地址：Android 模拟器上把 127.0.0.1 / localhost 替换为 10.0.2.2
  String get _resolvedHost {
    if (_host == null) return 'null';
    if (!Platform.isAndroid) return _host!;
    final lowerHost = _host!.toLowerCase();
    if (lowerHost == '127.0.0.1' || lowerHost == 'localhost') {
      return _emulatorHost;
    }
    return _host!;
  }

  String get baseUrl => 'http://$_resolvedHost:$_port';
  bool get isConnected => _host != null && _port != null && _token != null;

  Future<bool> loadFromStorage() async {
    final prefs = await SharedPreferences.getInstance();
    _host = prefs.getString(_hostKey);
    _port = prefs.getInt(_portKey);
    _token = prefs.getString(_tokenKey);
    return _host != null && _port != null && _token != null;
  }

  Future<void> saveConnection(String host, int port, String token) async {
    _host = host;
    _port = port;
    _token = token;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_hostKey, host);
    await prefs.setInt(_portKey, port);
    await prefs.setString(_tokenKey, token);
  }

  Future<void> _clearStored() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_hostKey);
    await prefs.remove(_portKey);
    await prefs.remove(_tokenKey);
  }

  Future<void> disconnect() async {
    _host = null;
    _port = null;
    _token = null;
    await _clearStored();
  }

  /// Set connection params without saving (used during pairing flow)
  void setConnectionParams(String host, int port) {
    _host = host;
    _port = port;
  }

  /// Pair request with a pairing code
  Future<Map<String, dynamic>> pairRequest(
      String code, String deviceName) async {
    final res = await _dio.post('$baseUrl/api/mobile/pair-request',
        data: {'code': code, 'device_name': deviceName});
    return res.data as Map<String, dynamic>;
  }

  /// Verify current token validity
  /// Returns 1 = valid, 0 = invalid/401 (token revoked), -1 = connection error (PC offline)
  Future<int> verifyTokenStatus() async {
    try {
      final res = await _dio.get('$baseUrl/api/mobile/verify');
      return res.statusCode == 200 ? 1 : 0;
    } on DioException catch (e) {
      if (e.response?.statusCode == 401) return 0;
      return -1;
    } catch (_) {
      return -1;
    }
  }

  /// Legacy — returns bool, treats all errors as invalid
  Future<bool> verifyToken() async {
    try {
      final res = await _dio.get('$baseUrl/api/mobile/verify');
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// 发起配对请求（新流程：mDNS 发现后调用）
  /// 如果后端返回 409（已有 pending），自动取消旧请求并重试一次
  Future<void> pairingRequest(String deviceName) async {
    try {
      await _dio.post('$baseUrl/api/mobile/pairing/request',
          data: {'device_name': deviceName});
    } on DioException catch (e) {
      if (e.response?.statusCode == 409) {
        // 旧 pending 卡住，自动取消后重试
        try {
          await _dio.post('$baseUrl/api/mobile/pairing/cancel');
        } catch (_) {}
        await _dio.post('$baseUrl/api/mobile/pairing/request',
            data: {'device_name': deviceName});
      } else {
        rethrow;
      }
    }
  }

  /// 提交配对码（新流程：用户在手机端输入配对码后调用）
  Future<String?> submitPairingCode(String code, String deviceName) async {
    final res = await _dio.post('$baseUrl/api/mobile/pairing/submit-code',
        data: {'code': code, 'device_name': deviceName});
    final data = res.data as Map<String, dynamic>;
    if (data['status'] == 'paired') {
      return data['token'] as String;
    }
    return null;
  }

  /// 取消配对请求（清除后端 _pending 状态，防止 409）
  Future<bool> cancelPairing() async {
    try {
      await _dio.post('$baseUrl/api/mobile/pairing/cancel');
      return true;
    } catch (e) {
      return false;
    }
  }

  /// 轮询配对状态：返回 {"status": "pending"} 或 {"status": "none"}
  Future<Map<String, dynamic>> getPairingStatus() async {
    final res = await _dio.get('$baseUrl/api/mobile/pairing/pending');
    return res.data as Map<String, dynamic>;
  }

  /// Get album tree
  Future<Map<String, dynamic>> getTree() async {
    final res = await _dio.get('$baseUrl/api/mobile/tree');
    return res.data as Map<String, dynamic>;
  }

  /// Get stats
  Future<Map<String, dynamic>> getStats() async {
    final res = await _dio.get('$baseUrl/api/mobile/stats');
    return res.data as Map<String, dynamic>;
  }

  /// Get photos for a path
  Future<Map<String, dynamic>> getPhotos(String path,
      {int page = 1, int pageSize = 100}) async {
    final res = await _dio.get('$baseUrl/api/mobile/photos', queryParameters: {
      'path': path,
      'page': page,
      'page_size': pageSize,
    });
    return res.data as Map<String, dynamic>;
  }

  /// Thumbnail URL（附带 token 供 Image.network 直接使用，不走 Dio 拦截器）
  String getThumbnailUrl(String path) =>
      '$baseUrl/api/mobile/thumbnail?path=${Uri.encodeComponent(path)}'
      '&token=${Uri.encodeComponent(_token ?? '')}';

  /// Full file URL
  String getFileUrl(String path) =>
      '$baseUrl/api/mobile/file?path=${Uri.encodeComponent(path)}'
      '&token=${Uri.encodeComponent(_token ?? '')}';

  /// Preview URL
  String getPreviewUrl(String path) =>
      '$baseUrl/api/mobile/preview?path=${Uri.encodeComponent(path)}'
      '&token=${Uri.encodeComponent(_token ?? '')}';

  /// Get EXIF
  Future<Map<String, dynamic>> getExif(String path) async {
    final res = await _dio
        .get('$baseUrl/api/mobile/exif', queryParameters: {'path': path});
    return res.data as Map<String, dynamic>;
  }

  /// Get sections (month list with counts, no photos)
  Future<Map<String, dynamic>> getPhotoSections(
      {int page = 1, int pageSize = 60}) async {
    final res = await _dio.get('$baseUrl/api/mobile/photos/sections',
            queryParameters: {'page': page, 'page_size': pageSize})
        // 客户端兜底：15s 还没收到首字节就主动抛 TimeoutException
        // （Dio 的 sendTimeout=30s 是最后保险，客户端 .timeout 更快失败）
        .timeout(const Duration(seconds: 15));
    return res.data as Map<String, dynamic>;
  }

  /// Get photos for a specific month (by-month endpoint)
  Future<Map<String, dynamic>> getPhotosByMonth(String month,
      {int page = 1, int pageSize = 60}) async {
    final res = await _dio.get('$baseUrl/api/mobile/photos/by-month',
        queryParameters: {
          'month': month,
          'page': page,
          'page_size': pageSize
        }).timeout(const Duration(seconds: 15));
    return res.data as Map<String, dynamic>;
  }

  /// Get all photos grouped by month (continuous grid for AlbumScreen)
  /// Returns: { sections: [{month, display, count, photos: [...], has_more_photos}],
  ///           has_more, available_months, page, page_size }
  Future<Map<String, dynamic>> getAllPhotosBySection({
    int page = 1,
    int pageSize = 6, // 每页几个月
    int photosPerSection = 60, // 每组最多返回几张
  }) async {
    final res =
        await _dio.get('$baseUrl/api/mobile/photos/all', queryParameters: {
      'page': page,
      'page_size': pageSize,
      'photos_per_section': photosPerSection,
    }).timeout(const Duration(seconds: 30));
    return res.data as Map<String, dynamic>;
  }

  /// Get folder listing
  Future<Map<String, dynamic>> getFolders({String? path}) async {
    final params = <String, dynamic>{};
    if (path != null && path.isNotEmpty) params['path'] = path;
    final res =
        await _dio.get('$baseUrl/api/mobile/folders', queryParameters: params);
    return res.data as Map<String, dynamic>;
  }

  /// Notify backend that file upload batch is complete
  Future<void> uploadDone() async {
    try {
      await _dio.post('$baseUrl/api/mobile/upload/done');
    } catch (_) {
      // 静默，不影响主流程
    }
  }

  /// Upload a file (streaming — does NOT load entire file into memory)
  Future<Map<String, dynamic>> uploadFile(String filePath, String fileName,
      {void Function(int sent, int total)? onProgress}) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromFileSync(filePath, filename: fileName),
    });
    final res = await _dio.post('$baseUrl/api/mobile/upload',
        data: formData, onSendProgress: onProgress);
    return res.data as Map<String, dynamic>;
  }
}
