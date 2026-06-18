import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static const String _tokenKey = 'mobile_token';
  static const String _hostKey = 'mobile_host';
  static const String _portKey = 'mobile_port';

  late final Dio _dio;
  String? _host;
  int? _port;
  String? _token;

  ApiClient() {
    _dio = Dio(BaseOptions(
      connectTimeout: const Duration(seconds: 5),
      receiveTimeout: const Duration(seconds: 10),
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        if (_token != null) {
          options.headers['Authorization'] = 'Bearer $_token';
        }
        handler.next(options);
      },
      onError: (error, handler) {
        if (error.response?.statusCode == 401) {
          _token = null;
          _clearStored();
        }
        handler.next(error);
      },
    ));
  }

  String? get host => _host;
  int? get port => _port;
  String get baseUrl => 'http://$_host:$_port';
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

  /// Full pairing flow: send pair request, then poll pair-status for confirmation
  /// Returns the token on success, or null on failure
  Future<String?> pairAndPoll(String code, String deviceName, {
    int maxRetries = 30,
    Duration interval = const Duration(seconds: 2),
  }) async {
    final result = await pairRequest(code, deviceName);
    if (result['status'] != 'pending') return null;

    // Poll /api/mobile/pair-status?code=XXX until accepted or expired
    for (int i = 0; i < maxRetries; i++) {
      await Future.delayed(interval);
      try {
        final res = await _dio.get('$baseUrl/api/mobile/pair-status',
            queryParameters: {'code': code});
        final data = res.data as Map<String, dynamic>;
        final status = data['status'] as String;
        if (status == 'accepted' && data.containsKey('token')) {
          _token = data['token'] as String;
          await saveConnection(_host!, _port!, _token!);
          return _token!;
        }
        if (status == 'expired' || status == 'invalid') {
          return null;
        }
        // status == 'pending' → continue polling
      } on DioException catch (e) {
        // 404 = invalid code, 410 = expired
        if (e.response?.statusCode == 404 || e.response?.statusCode == 410) {
          return null;
        }
        // Other errors → continue polling
      }
    }
    return null;
  }

  /// Pair request with a pairing code
  Future<Map<String, dynamic>> pairRequest(String code, String deviceName) async {
    final res = await _dio.post('$baseUrl/api/mobile/pair-request',
        data: {'code': code, 'device_name': deviceName});
    return res.data as Map<String, dynamic>;
  }

  /// Verify current token validity
  Future<bool> verifyToken() async {
    try {
      final res = await _dio.get('$baseUrl/api/mobile/verify');
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// 发起配对请求（新流程：mDNS 发现后调用）
  Future<void> pairingRequest(String deviceName) async {
    await _dio.post('$baseUrl/api/mobile/pairing/request',
        data: {'device_name': deviceName});
  }

  /// 提交配对码（新流程：用户在手机端输入配对码后调用）
  Future<String?> submitPairingCode(String code, String deviceName) async {
    final res = await _dio.post(
      '$baseUrl/api/mobile/pairing/submit-code',
      data: {'code': code, 'device_name': deviceName});
    final data = res.data as Map<String, dynamic>;
    if (data['status'] == 'paired') {
      return data['token'] as String;
    }
    return null;
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

  /// Thumbnail URL
  String getThumbnailUrl(String path) =>
      '$baseUrl/api/mobile/thumbnail?path=${Uri.encodeComponent(path)}';

  /// Full file URL
  String getFileUrl(String path) =>
      '$baseUrl/api/mobile/file?path=${Uri.encodeComponent(path)}';

  /// Preview URL
  String getPreviewUrl(String path) =>
      '$baseUrl/api/mobile/preview?path=${Uri.encodeComponent(path)}';

  /// Get EXIF
  Future<Map<String, dynamic>> getExif(String path) async {
    final res = await _dio.get('$baseUrl/api/mobile/exif',
        queryParameters: {'path': path});
    return res.data as Map<String, dynamic>;
  }

  /// Upload a file
  Future<Map<String, dynamic>> uploadFile(
      String filePath, String fileName, List<int> bytes,
      {void Function(int sent, int total)? onProgress}) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(bytes, filename: fileName),
    });
    final res = await _dio.post('$baseUrl/api/mobile/upload',
        data: formData, onSendProgress: onProgress);
    return res.data as Map<String, dynamic>;
  }
}
