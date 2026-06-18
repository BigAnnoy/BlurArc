import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../services/mdns_discovery.dart';
import 'pairing_code_screen.dart';

class ConnectScreen extends StatefulWidget {
  const ConnectScreen({super.key});

  @override
  State<ConnectScreen> createState() => _ConnectScreenState();
}

class _ConnectScreenState extends State<ConnectScreen> {
  final _mdns = MdnsDiscovery();
  final _discovered = <DiscoveredService>[];
  bool _isScanning = true;
  String _statusMessage = '';

  @override
  void initState() {
    super.initState();
    _startDiscovery();
  }

  @override
  void dispose() {
    _mdns.dispose();
    super.dispose();
  }

  Future<void> _startDiscovery() async {
    setState(() {
      _isScanning = true;
      _discovered.clear();
      _statusMessage = '正在扫描局域网...';
    });

    try {
      await for (final service in _mdns.discover()) {
        setState(() {
          // 去重
          if (!_discovered.any((s) => s.host == service.host && s.port == service.port)) {
            _discovered.add(service);
          }
        });
      }
    } catch (_) {}
    setState(() {
      _isScanning = false;
      if (_discovered.isEmpty) {
        _statusMessage = '未找到 Blur Arc 服务，请手动输入';
      } else {
        _statusMessage = '找到 ${_discovered.length} 个服务';
      }
    });
  }

  Future<void> _onDeviceTap(DiscoveredService service) async {
    setState(() => _statusMessage = '正在发送配对请求...');

    try {
      final api = ApiClient();
      api.setConnectionParams(service.host, service.port);
      await api.pairingRequest('BlurArc Mobile');

      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => PairingCodeScreen(
            api: api,
            deviceName: service.name,
          ),
        ),
      );
    } catch (e) {
      setState(() => _statusMessage = '配对请求失败: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('连接电脑'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isScanning ? null : _startDiscovery,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.photo_album, size: 64, color: Color(0xFF22D3EE)),
            const SizedBox(height: 16),
            const Text('Blur Arc',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(_statusMessage,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: Colors.grey)),
            const SizedBox(height: 24),

            if (_isScanning && _discovered.isEmpty)
              const Center(child: CircularProgressIndicator())
            else if (_discovered.isEmpty)
              _buildManualEntry()
            else
              Expanded(child: _buildDeviceList()),
          ],
        ),
      ),
    );
  }

  Widget _buildDeviceList() {
    return ListView.builder(
      itemCount: _discovered.length,
      itemBuilder: (context, index) {
        final service = _discovered[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: ListTile(
            leading: const Icon(Icons.computer, size: 40, color: Color(0xFF22D3EE)),
            title: Text(service.name),
            subtitle: Text('${service.host}:${service.port}'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _onDeviceTap(service),
          ),
        );
      },
    );
  }

  Widget _buildManualEntry() {
    final hostController = TextEditingController();
    final portController = TextEditingController(text: '8900');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('手动输入连接信息', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        TextField(
          controller: hostController,
          decoration: const InputDecoration(
            labelText: '电脑 IP 地址',
            hintText: '192.168.1.xxx',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: portController,
          decoration: const InputDecoration(
            labelText: '端口',
            hintText: '8900',
            border: OutlineInputBorder(),
          ),
          keyboardType: TextInputType.number,
        ),
        const SizedBox(height: 12),
        FilledButton(
          onPressed: () {
            final host = hostController.text.trim();
            final port = int.tryParse(portController.text.trim()) ?? 8900;
            if (host.isEmpty) return;
            _onDeviceTap(DiscoveredService(
              name: 'Manual',
              host: host,
              port: port,
            ));
          },
          child: const Text('连接'),
        ),
      ],
    );
  }
}
