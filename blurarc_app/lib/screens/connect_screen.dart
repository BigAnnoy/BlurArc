import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import '../services/device_info_service.dart';
import '../services/mdns_discovery.dart';
import '../widgets/blur_arc_logo.dart';
import '../widgets/step_indicator.dart';
import 'pairing_code_screen.dart';
import 'home_page.dart';

class ConnectScreen extends StatefulWidget {
  const ConnectScreen({super.key});

  @override
  State<ConnectScreen> createState() => _ConnectScreenState();
}

class _ConnectScreenState extends State<ConnectScreen> {
  final _mdns = MdnsDiscovery();
  final _discovered = <DiscoveredService>[];
  bool _isScanning = true;
  bool _checkingToken = true;
  String _statusMessage = '';
  bool _pcOffline = false;

  @override
  void initState() {
    super.initState();
    _checkStoredToken();
  }

  Future<void> _checkStoredToken() async {
    final api = ApiClient();
    final hasStored = await api.loadFromStorage();

    if (hasStored) {
      final status = await api.verifyTokenStatus();

      if (status == 1 && mounted) {
        // 场景：token 有效，直接连接，设置断开回调
        api.onDisconnected = () {
          // 不清 token（类似场景 1），下次返回连接页时自动检测
        };
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => HomePage(api: api)),
          (route) => false,
        );
        return;
      } else if (status == -1) {
        // 场景 1：PC 端没开，保留 token，显示提示
        if (mounted) {
          setState(() {
            _checkingToken = false;
            _pcOffline = true;
            _statusMessage = 'PC 端未开启，请先启动 Blur Arc';
          });
        }
        _startDiscovery();
        return;
      }
      // 场景 2：token 被撤销（401），清除后让用户重新配对
      await api.disconnect();
      if (mounted) {
        setState(() => _statusMessage = '配对已失效，请重新配对');
      }
    }

    setState(() => _checkingToken = false);
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
          if (!_discovered
              .any((s) => s.host == service.host && s.port == service.port)) {
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
      // 用真实设备名（Pixel 7 / iPhone 15 等）作为配对请求中的 device_name
      final deviceName = await DeviceInfoService.getDeviceName();
      await api.pairingRequest(deviceName);

      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => PairingCodeScreen(
            api: api,
            deviceName: deviceName,
            onCancel: () {
              setState(() {});
            },
          ),
        ),
      );
    } catch (e) {
      final msg = e.toString().toLowerCase();
      String display;
      if (msg.contains('socket') ||
          msg.contains('connection') ||
          msg.contains('refused') ||
          msg.contains('timeout') ||
          msg.contains('failed host lookup') ||
          msg.contains('network')) {
        display = '未找到设备，请检查地址和端口';
      } else {
        display = '连接失败，请重试';
      }
      setState(() => _statusMessage = display);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const BlurArcLogoWithText(height: 37),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isScanning ? null : _startDiscovery,
          ),
        ],
      ),
      body: _checkingToken
          ? const Center(child: CircularProgressIndicator())
          : _pcOffline
              ? Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.wifi_off,
                            size: 64, color: Colors.grey),
                        const SizedBox(height: 16),
                        const Text('PC 端未开启',
                            style: TextStyle(
                                fontSize: 18, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        Text(_statusMessage,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                                fontSize: 14, color: Colors.grey)),
                        const SizedBox(height: 24),
                        FilledButton.icon(
                          onPressed: () {
                            setState(() => _pcOffline = false);
                            _startDiscovery();
                          },
                          icon: const Icon(Icons.refresh),
                          label: const Text('重新搜索'),
                        ),
                      ],
                    ),
                  ),
                )
              : _buildDiscoveryBody(),
    );
  }

  /// 第一步：发现设备 body
  /// - 有设备列表：Column + Expanded(ListView) 填满剩余空间
  /// - 无设备列表（手动输入）：SingleChildScrollView 防止小屏 overflow
  Widget _buildDiscoveryBody() {
    final hasDevices = _discovered.isNotEmpty;

    if (hasDevices) {
      return Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
            child: Column(
              children: [
                Text(_statusMessage,
                    style: const TextStyle(fontSize: 14, color: Colors.grey)),
                const SizedBox(height: 12),
                const StepIndicator(currentStep: 1, totalSteps: 2),
                const SizedBox(height: 8),
                const Text('步骤 1/2：连接设备', style: TextStyle(fontSize: 14)),
                const SizedBox(height: 8),
              ],
            ),
          ),
          Expanded(child: _buildDeviceList()),
        ],
      );
    }

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(_statusMessage,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: Colors.grey)),
            const SizedBox(height: 16),
            const StepIndicator(currentStep: 1, totalSteps: 2),
            const SizedBox(height: 8),
            const Text('步骤 1/2：连接设备',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 14)),
            const SizedBox(height: 24),
            if (_isScanning)
              const Center(child: CircularProgressIndicator())
            else
              _buildManualEntry(),
          ],
        ),
      ),
    );
  }

  Widget _buildDeviceList() {
    final theme = Theme.of(context);
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
      itemCount: _discovered.length,
      itemBuilder: (context, index) {
        final service = _discovered[index];
        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Material(
            color: theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(10),
            child: InkWell(
              onTap: () => _onDeviceTap(service),
              borderRadius: BorderRadius.circular(10),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: theme.dividerColor, width: 0.5),
                ),
                child: Row(
                  children: [
                    // 设备图标方块（原型：40x40 圆角 8 容器 + 💻 emoji）
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: theme.brightness == Brightness.dark
                            ? const Color(0xFF1a2533)
                            : const Color(0xFFeef1f6),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      alignment: Alignment.center,
                      child: const Text('💻', style: TextStyle(fontSize: 20)),
                    ),
                    const SizedBox(width: 12),
                    // 设备名 + IP
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            service.name,
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w500,
                              color: theme.colorScheme.onSurface,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${service.host}:${service.port}',
                            style: TextStyle(
                              fontSize: 12,
                              color: theme.colorScheme.onSurface.withAlpha(150),
                            ),
                          ),
                        ],
                      ),
                    ),
                    // 状态点
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: Color(0xFF22c55e),
                        shape: BoxShape.circle,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildManualEntry() {
    final hostController = TextEditingController();
    final portController = TextEditingController(text: '8900');
    final theme = Theme.of(context);
    // 原型：surface2 圆角容器内嵌两个 input + 冒号
    final inputGroupDecoration = BoxDecoration(
      color: theme.brightness == Brightness.dark
          ? const Color(0xFF1a2533)
          : const Color(0xFFf0f1f3),
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: theme.dividerColor, width: 0.5),
    );
    final ipBorder = OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
      borderSide: BorderSide.none,
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('或手动输入',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.all(4),
          decoration: inputGroupDecoration,
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: hostController,
                  style: TextStyle(
                    fontSize: 15,
                    color: theme.colorScheme.onSurface,
                  ),
                  decoration: InputDecoration(
                    hintText: 'IP 地址',
                    border: ipBorder,
                    focusedBorder: ipBorder,
                    enabledBorder: ipBorder,
                    filled: true,
                    fillColor: Colors.transparent,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 12),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Text(':',
                    style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface.withAlpha(180))),
              ),
              SizedBox(
                width: 80,
                child: TextField(
                  controller: portController,
                  style: TextStyle(
                    fontSize: 15,
                    color: theme.colorScheme.onSurface,
                  ),
                  decoration: InputDecoration(
                    hintText: '8900',
                    border: ipBorder,
                    focusedBorder: ipBorder,
                    enabledBorder: ipBorder,
                    filled: true,
                    fillColor: Colors.transparent,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 12),
                  ),
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
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
