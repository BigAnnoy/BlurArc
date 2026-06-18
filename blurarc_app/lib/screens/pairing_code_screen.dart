import 'package:flutter/material.dart';
import '../services/api_client.dart';
import 'home_page.dart';

class PairingCodeScreen extends StatefulWidget {
  final ApiClient api;
  final String deviceName;

  const PairingCodeScreen({
    required this.api,
    required this.deviceName,
    super.key,
  });

  @override
  State<PairingCodeScreen> createState() => _PairingCodeScreenState();
}

class _PairingCodeScreenState extends State<PairingCodeScreen> {
  final _codeControllers = List.generate(6, (_) => TextEditingController());
  final _focusNodes = List.generate(6, (_) => FocusNode());
  bool _isSubmitting = false;
  String? _error;

  String get _code => _codeControllers.map((c) => c.text).join();

  @override
  void dispose() {
    for (final c in _codeControllers) {
      c.dispose();
    }
    for (final n in _focusNodes) {
      n.dispose();
    }
    super.dispose();
  }

  Future<void> _submitCode() async {
    if (_code.length != 6) return;

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      final token = await widget.api.submitPairingCode(_code, widget.deviceName);
      if (token != null) {
        // 保存连接信息
        await widget.api.saveConnection(widget.api.host!, widget.api.port!, token);
        if (!mounted) return;
        // 跳转到相册页
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (_) => HomePage(api: widget.api),
          ),
        );
      } else {
        setState(() => _error = '配对失败，请重试');
      }
    } catch (e) {
      // 提供更具体的错误信息
      final errMsg = e.toString();
      String errorMsg;
      final errStr = errMsg.toLowerCase();
      if (errStr.contains('socket') || errStr.contains('connection') || errStr.contains('timeout') || errStr.contains('failed to connect')) {
        errorMsg = '网络连接失败，请检查 PC 和手机是否在同一局域网';
      } else if (errStr.contains('400') || errStr.contains('invalid') || errStr.contains('配对码')) {
        errorMsg = '配对码错误或已过期，请重新输入';
      } else if (errStr.contains('500') || errStr.contains('server')) {
        errorMsg = '服务器错误，请稍后重试';
      } else {
        final displayMsg = errMsg.length > 50 ? '${errMsg.substring(0, 50)}...' : errMsg;
        errorMsg = '配对失败: $displayMsg';
      }
      setState(() {
        _error = errorMsg;
      });
    } finally {
      setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('输入配对码')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.key, size: 64, color: Color(0xFF22D3EE)),
            const SizedBox(height: 24),
            const Text(
              '请在电脑上确认配对',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              '电脑确认后，请输入显示的 6 位配对码',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14, color: Colors.grey),
            ),
            const SizedBox(height: 32),

            // 6 位输入框
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(6, (i) {
                return Container(
                  width: 48,
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  child: TextField(
                    controller: _codeControllers[i],
                    focusNode: _focusNodes[i],
                    textAlign: TextAlign.center,
                    maxLength: 1,
                    style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                    decoration: InputDecoration(
                      counterText: '',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: Color(0xFF22D3EE), width: 2),
                      ),
                    ),
                    onChanged: (v) {
                      if (v.isNotEmpty && i < 5) {
                        _focusNodes[i + 1].requestFocus();
                      }
                      if (_code.length == 6) {
                        _submitCode();
                      }
                    },
                  ),
                );
              }),
            ),

            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(
                _error!,
                style: const TextStyle(color: Colors.red, fontSize: 14),
                textAlign: TextAlign.center,
              ),
            ],

            const SizedBox(height: 32),

            if (_isSubmitting)
              const CircularProgressIndicator()
            else
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _code.length == 6 ? _submitCode : null,
                  child: const Text('确认'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
