import 'package:flutter_test/flutter_test.dart';
import 'package:blurarc_app/services/api_client.dart';

void main() {
  group('ApiClient', () {
    test('baseUrl returns correct format', () {
      final api = ApiClient();
      api.setConnectionParams('192.168.1.100', 8900);
      expect(api.baseUrl, 'http://192.168.1.100:8900');
    });

    test('isConnected is false initially', () {
      final api = ApiClient();
      expect(api.isConnected, false);
    });

    test('thumbnail URL format', () {
      final api = ApiClient();
      api.setConnectionParams('192.168.1.100', 8900);
      final url = api.getThumbnailUrl('/photos/2024/test.jpg');
      expect(url, contains('192.168.1.100:8900'));
      expect(url, contains('thumbnail'));
    });

    test('file URL format', () {
      final api = ApiClient();
      api.setConnectionParams('192.168.1.100', 8900);
      final url = api.getFileUrl('/photos/2024/test.jpg');
      expect(url, contains('192.168.1.100:8900'));
      expect(url, contains('file'));
    });
  });
}
