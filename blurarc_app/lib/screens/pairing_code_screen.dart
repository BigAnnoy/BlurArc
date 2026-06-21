import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/api_client.dart';
import '../widgets/blur_arc_logo.dart';
import '../widgets/step_indicator.dart';
import 'home_page.dart';

class PairingCodeScreen extends StatefulWidget {
  final ApiClient api;
  final String deviceName;
  final VoidCallback? onCancel;

  const PairingCodeScreen({
    required this.api,
    required this.deviceName,
    this.onCancel,
    super.key,
  });

  @override
  State<PairingCodeScreen> createState() => _PairingCodeScreenState();
}

class _PairingCodeScreenState extends State<PairingCodeScreen> {
  final _codeControllers = List.generate(6, (_) => TextEditingController());
  final _focusNodes = List.generate(6, (_) => FocusNode());
  bool _codeGenerated = false;
  bool _isSubmitting = false;
  bool _timeout = false;
  bool _rejected = false;
  String? _error;
  Timer? _pollTimer;

  String get _code => _codeControllers.map((c) => c.text).join();

  @override
  void initState() {
    super.initState();
    _startPolling();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    for (final c in _codeControllers) {
      c.dispose();
    }
    for (final n in _focusNodes) {
      n.dispose();
    }
    super.dispose();
  }

  void _startPolling() {
    int elapsed = 0;
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      elapsed += 2;
      if (elapsed > 120) {
        _pollTimer?.cancel();
        await widget.api.cancelPairing();
        if (mounted) setState(() => _timeout = true);
        return;
      }
      try {
        final res = await widget.api.getPairingStatus();
        final status = res['status'] as String?;
        // 只要收到 "confirmed"（无论是否经过 "pending"），立即跳转输入码界面
        // 这修复了 PC 快速确认时 wasPending 始终为 false 导致状态不更新的竞争条件
        if (status == 'confirmed') {
          _pollTimer?.cancel();
          if (mounted) {
            setState(() => _codeGenerated = true);
            _focusNodes[0].requestFocus();
          }
        } else if (status == 'rejected') {
          _pollTimer?.cancel();
          if (mounted) setState(() => _rejected = true);
        }
        // "pending" / "none"：继续等待
      } catch (_) {}
    });
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
        await widget.api.saveConnection(widget.api.host!, widget.api.port!, token);
        if (!mounted) return;
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(
            builder: (_) => HomePage(api: widget.api),
          ),
          (route) => false,
        );
      } else {
        setState(() => _error = '配对失败，请重试');
      }
    } catch (e) {
      final errMsg = e.toString().toLowerCase();
      String errorMsg;
      if (errMsg.contains('socket') || errMsg.contains('connection') || errMsg.contains('timeout')) {
        errorMsg = '网络连接失败，请检查网络';
      } else if (errMsg.contains('400') || errMsg.contains('invalid')) {
        errorMsg = '配对码错误或已过期，请重新输入';
      } else {
        errorMsg = '配对失败，请重试';
      }
      setState(() => _error = errorMsg);
    } finally {
      setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const BlurArcLogoWithText(logoSize: 20, fontSize: 14)),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              if (_rejected) ...[
                const Icon(Icons.cancel, size: 48, color: Colors.red),
                const SizedBox(height: 16),
                const Text(
                  '配对请求被拒绝',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                const Text(
                  '电脑端拒绝了配对请求，请重试',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 14, color: Colors.grey),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('返回'),
                  ),
                ),
              ] else if (!_codeGenerated && !_timeout) ...[
                const Icon(Icons.key, size: 64, color: Color(0xFF22D3EE)),
                const SizedBox(height: 24),
                const Text(
                  '配对请求已发送',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                const Text(
                  '请在电脑端确认配对',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 14, color: Colors.grey),
                ),
                const SizedBox(height: 32),
                const SizedBox(
                  width: 24, height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2.5),
                ),
                const SizedBox(height: 24),
                Text(
                  '等待电脑确认...',
                  style: TextStyle(fontSize: 14, color: Colors.grey[400]),
                ),
                const SizedBox(height: 24),
                TextButton(
                  onPressed: () async {
                    _pollTimer?.cancel();
                    final navigator = Navigator.of(context);  // 在 await 前获取 navigator
                    await widget.api.cancelPairing();
                    if (mounted) {
                      widget.onCancel?.call();
                      navigator.pop();
                    }
                  },
                  child: const Text('取消'),
                ),
              ] else if (_timeout) ...[
              const Icon(Icons.timer_off, size: 48, color: Colors.red),
              const SizedBox(height: 16),
              const Text(
                '配对超时',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              const Text(
                '请在电脑端确认配对，然后返回重试',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, color: Colors.grey),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('返回'),
                ),
              ),
            ] else ...[
              Icon(Icons.key, size: 64, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 16),
              // Step indicator
              const StepIndicator(currentStep: 2, totalSteps: 2),
              const SizedBox(height: 8),
              const Text('步骤 2/2：输入配对码',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 14)),
              const SizedBox(height: 16),
              const Text(
                '在电脑端查看配对码并输入',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, color: Colors.grey),
              ),
              const SizedBox(height: 32),

              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(6, (i) {
                  return Container(
                    width: 40,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    child: KeyboardListener(
                      focusNode: FocusNode(),
                      onKeyEvent: (event) {
                        if (event is KeyDownEvent &&
                            event.logicalKey == LogicalKeyboardKey.backspace &&
                            _codeControllers[i].text.isEmpty &&
                            i > 0) {
                          _focusNodes[i - 1].requestFocus();
                          _codeControllers[i - 1].clear();
                        }
                      },
                      child: TextField(
                        controller: _codeControllers[i],
                        focusNode: _focusNodes[i],
                        textAlign: TextAlign.center,
                        maxLength: 1,
                        keyboardType: TextInputType.text,
                        textCapitalization: TextCapitalization.characters,
                        style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                        decoration: InputDecoration(
                          counterText: '',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                            borderSide: const BorderSide(color: Color(0xFF22D3EE), width: 2),
                          ),
                          contentPadding: const EdgeInsets.symmetric(vertical: 10),
                        ),
                        onChanged: (v) {
                          if (v.isNotEmpty) {
                            if (i < 5) {
                              _focusNodes[i + 1].requestFocus();
                            }
                          } else {
                            // 退格清空当前框，跳回上一个框
                            if (i > 0) {
                              _focusNodes[i - 1].requestFocus();
                            }
                          }
                          if (_code.length == 6) {
                            _submitCode();
                          }
                        },
                      ),
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
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _isSubmitting ? null : () => Navigator.pop(context),
                        child: const Text('返回'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton(
                        onPressed: _isSubmitting ? null : (_code.length == 6 ? _submitCode : null),
                        child: const Text('确认配对'),
                      ),
                    ),
                  ],
                ),
            ],
          ],
        ),
      ),
      ),
    );
  }
}
