# 手机配对与发现流程重设计 — 实现计划

> **For agentic workers:** Use `subagent-driven-development` or `executing-plans` to implement this plan phase-by-phase. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Spec:** `docs/superpowers/specs/2026-06-18-mobile-pairing-redesign.md`
>
> **Prerequisite:** Phase 1-6 of `2026-06-18-mobile-app-plan.md` 已完成（现有移动接入功能基线）

**Goal:** 将现有手动输入 IP/端口或扫码配对的流程，重设计为**零配置 mDNS 自动发现 + 配对码二次验证**流程。

**Tech Stack:** Python (Flask, zeroconf), Dart/Flutter (multicast_dns), TypeScript (React 19)

---

## ✅ 实现进度总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| **Phase 1** | ⬜ 待实现 | 后端 mDNS 广播 (ZeroconfPublisher) |
| **Phase 2** | ⬜ 待实现 | 后端 PairingManager（配对码生成/验证） |
| **Phase 3** | ⬜ 待实现 | 后端新增配对 API 端点 + 桥接端点 |
| **Phase 4** | ⬜ 待实现 | PC 前端 MobileDeviceManager 重设计 |
| **Phase 5** | ⬜ 待实现 | Flutter 连接页 mDNS 发现重写 |
| **Phase 6** | ⬜ 待实现 | Flutter 配对码输入页 |
| **Phase 7** | ⬜ 待实现 | Flutter 首页三 Tab 重设计 |
| **Phase 8** | ⬜ 待实现 | 单元测试 + 集成测试 |

---

## 文件变更总览

```
新增:
  backend/zeroconf_publisher.py          # mDNS 广播（可独立复用）
  flutter_app/lib/services/mdns_discovery.dart  # mDNS 发现服务
  flutter_app/lib/screens/pairing_code_screen.dart  # 配对码输入页
  flutter_app/lib/widgets/photo_waterfall.dart  # 相册瀑布流组件
  test/unit/test_zeroconf_publisher.py  # ZeroconfPublisher 测试
  test/unit/test_pairing_manager.py      # PairingManager 测试

修改:
  backend/mobile_access_server.py         # 集成 ZeroconfPublisher + PairingManager
  backend/api_server.py                  # 新增 /api/mobile/pairing/* 桥接端点
  frontend/src/components/dialogs/MobileDeviceManager.tsx  # 双开关 + 配对三状态
  frontend/src/services/api.ts           # 新增 pairing API 方法
  frontend/src/contexts/I18nContext.tsx # 新增 i18n 字符串
  flutter_app/lib/services/api_client.dart  # 重写 pairAndPoll 为配对码流程
  flutter_app/lib/screens/connect_screen.dart  # 重写为 mDNS 发现
  flutter_app/lib/screens/album_screen.dart  # 改为三 Tab 首页
  flutter_app/lib/app.dart               # 路由调整
  flutter_app/pubspec.yaml              # 确认 multicast_dns 依赖
  requirements.txt                       # 新增 zeroconf>=0.132.0
```

---

## Phase 1 — 后端 mDNS 广播

> 目标：PC 端开启配对模式后，通过 mDNS 广播自身，手机端可自动发现。

### 1.1 新增 `backend/zeroconf_publisher.py`

独立模块，便于单独测试和复用。

```python
# backend/zeroconf_publisher.py
from __future__ import annotations

import logging
import socket
import threading
from pathlib import Path

from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_blurarc._tcp.local."
SERVICE_NAME_TEMPLATE = "Blur Arc on {hostname}._blurarc._tcp.local."


class ZeroconfPublisher:
    """mDNS 服务广播器"""

    def __init__(self, port: int, app_name: str = "Blur Arc"):
        self.port = port
        self.app_name = app_name
        self._zc: Zeroconf | None = None
        self._info: ServiceInfo | None = None
        self._thread: threading.Thread | None = None

    @staticmethod
    def _get_local_ip() -> str:
        """获取局域网 IP"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    def start(self) -> None:
        """开始广播（异步，不阻塞主线程）"""
        if self._zc is not None:
            logger.warning("[Zeroconf] 已在广播中")
            return

        def _run():
            try:
                local_ip = self._get_local_ip()
                address = socket.inet_aton(local_ip)
                hostname = socket.gethostname()

                self._info = ServiceInfo(
                    SERVICE_TYPE,
                    SERVICE_NAME_TEMPLATE.format(hostname=hostname),
                    addresses=[address],
                    port=self.port,
                    properties={
                        "app": self.app_name,
                        "version": "1.0",
                        "hostname": hostname,
                    },
                )
                self._zc = Zeroconf()
                self._zc.register_service(self._info)
                logger.info(f"[Zeroconf] 广播已启动: {local_ip}:{self.port}")
            except Exception as e:
                logger.error(f"[Zeroconf] 启动失败: {e}")

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止广播"""
        if self._zc is not None:
            try:
                self._zc.unregister_all_services()
                self._zc.close()
                logger.info("[Zeroconf] 广播已停止")
            except Exception as e:
                logger.error(f"[Zeroconf] 停止失败: {e}")
            finally:
                self._zc = None
                self._info = None

    def is_running(self) -> bool:
        return self._zc is not None
```

**要点：**
- `start()` 在新线程执行，避免阻塞调用方
- `socket.inet_aton()` 将 IP 转为 4 字节地址（zeroconf 要求）
- `SERVICE_TYPE = "_blurarc._tcp.local."` — 手机端用同类型查询

### 1.2 安装 zeroconf 依赖

```bash
pip install zeroconf>=0.132.0
```

更新 `requirements.txt` 添加 `zeroconf>=0.132.0`。

### 1.3 单元测试

`test/unit/test_zeroconf_publisher.py`：

```python
import pytest
from backend.zeroconf_publisher import ZeroconfPublisher

class TestZeroconfPublisher:
    def test_init(self):
        p = ZeroconfPublisher(8900)
        assert p.port == 8900
        assert not p.is_running()

    def test_start_stop(self):
        p = ZeroconfPublisher(8900)
        p.start()
        # 等待线程启动
        import time; time.sleep(1)
        assert p.is_running()
        p.stop()
        assert not p.is_running()

    def test_double_start_no_error(self):
        p = ZeroconfPublisher(8900)
        p.start()
        p.start()  # 不应抛异常
        p.stop()
```

---

## Phase 2 — 后端 PairingManager

> 目标：管理配对码生成、验证、过期、待确认设备队列。

### 2.1 在 `backend/mobile_access_server.py` 中新增 `PairingManager` 类

```python
# backend/mobile_access_server.py（新增在文件顶部附近）

import secrets
import string
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

PAIRING_CODE_LENGTH = 6
PAIRING_CODE_TTL = 120  # 秒


@dataclass
class PendingPairing:
    """待确认的配对请求"""
    device_name: str
    requested_at: float
    status: str = "pending"  # pending | confirmed | rejected


class PairingManager:
    """配对码管理器"""

    def __init__(self):
        self._current_code: Optional[str] = None
        self._code_expires_at: float = 0
        self._pending: Optional[PendingPairing] = None
        self._confirmed_devices: List[Dict] = []  # [{device_name, code, confirmed_at}]

    def generate_code(self) -> str:
        """生成新的配对码（确认配对时调用）"""
        self._current_code = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(PAIRING_CODE_LENGTH)
        )
        self._code_expires_at = time.time() + PAIRING_CODE_TTL
        logger.info(f"[Pairing] 生成配对码: {self._current_code}")
        return self._current_code

    def verify_code(self, code: str) -> bool:
        """验证配对码（手机端提交时调用）"""
        if time.time() > self._code_expires_at:
            logger.warning("[Pairing] 配对码已过期")
            return False
        if self._current_code is None:
            return False
        result = secrets.compare_digest(self._current_code, code.upper())
        if result:
            logger.info("[Pairing] 配对码验证成功")
        else:
            logger.warning("[Pairing] 配对码验证失败")
        return result

    def consume_code(self) -> None:
        """验证成功后消费掉配对码（一次性）"""
        self._current_code = None
        self._code_expires_at = 0

    def set_pending(self, device_name: str) -> None:
        """设置待确认设备"""
        self._pending = PendingPairing(device_name=device_name, requested_at=time.time())

    def get_pending(self) -> Optional[PendingPairing]:
        """获取待确认设备（PC 端轮询用）"""
        return self._pending if self._pending and self._pending.status == "pending" else None

    def confirm_pending(self) -> str:
        """确认配对 → 生成配对码并返回"""
        if not self._pending:
            raise RuntimeError("没有待确认的配对请求")
        self._pending.status = "confirmed"
        return self.generate_code()

    def reject_pending(self) -> None:
        """拒绝配对"""
        if self._pending:
            self._pending.status = "rejected"

    def clear_pending(self) -> None:
        """清除待确认状态"""
        self._pending = None

    def is_code_valid(self) -> bool:
        """配对码是否在有效期内"""
        return time.time() <= self._code_expires_at and self._current_code is not None
```

### 2.2 集成到 `MobileAccessServer`

在 `MobileAccessServer.__init__` 中新增：

```python
self._pairing = PairingManager()
self._zeroconf: Optional[ZeroconfPublisher] = None
```

新增方法：

```python
def start_pairing_mode(self) -> dict:
    """开启配对模式：启动 mDNS 广播"""
    if self._zeroconf is None:
        self._zeroconf = ZeroconfPublisher(self.port)
    self._zeroconf.start()
    return {"status": "broadcasting", "hostname": socket.gethostname()}

def stop_pairing_mode(self) -> None:
    """停止配对模式：停止 mDNS 广播，清除待确认"""
    if self._zeroconf:
        self._zeroconf.stop()
        self._zeroconf = None
    self._pairing.clear_pending()
    self._pairing.consume_code()  # 使当前配对码失效
```

### 2.3 单元测试

`test/unit/test_pairing_manager.py`：

```python
import time
import pytest
from backend.mobile_access_server import PairingManager, PAIRING_CODE_TTL

class TestPairingManager:
    def test_generate_and_verify(self):
        pm = PairingManager()
        code = pm.generate_code()
        assert len(code) == 6
        assert pm.verify_code(code) is True

    def test_verify_wrong_code(self):
        pm = PairingManager()
        pm.generate_code()
        assert pm.verify_code("WRONG1") is False

    def test_code_expires(self, monkeypatch):
        pm = PairingManager()
        pm.generate_code()
        # 模拟时间过期
        monkeypatch.setattr(time, "time", lambda: time.time() + PAIRING_CODE_TTL + 1)
        assert pm.verify_code(pm._current_code) is False

    def test_consume_code(self):
        pm = PairingManager()
        pm.generate_code()
        pm.consume_code()
        assert pm._current_code is None

    def test_pending_flow(self):
        pm = PairingManager()
        pm.set_pending("Pixel 8")
        pending = pm.get_pending()
        assert pending is not None
        assert pending.device_name == "Pixel 8"

        code = pm.confirm_pending()
        assert len(code) == 6

        # 确认后 get_pending 应返回 None（已确认）
        assert pm.get_pending() is None

    def test_reject_pending(self):
        pm = PairingManager()
        pm.set_pending("Pixel 8")
        pm.reject_pending()
        assert pm.get_pending() is None
```

---

## Phase 3 — 后端新增配对 API 端点

> 目标：为新的配对流程提供 HTTP API。

### 3.1 移动接入服务直接端点（端口 8900-8999）

在 `MobileAccessServer._register_routes` 中新增：

```python
# ============== 重设计配对端点 ==============

@self.app.route("/api/mobile/pairing/request", methods=["POST"])
def pairing_request():
    """手机端发起配对请求"""
    data = request.get_json(force=True, silent=True) or {}
    device_name = data.get("device_name", "Unknown")
    
    if server._pairing.get_pending() is not None:
        return jsonify({"error": "已有待确认的配对请求"}), 409
    
    server._pairing.set_pending(device_name)
    logger.info(f"[Pairing] 收到配对请求: {device_name}")
    return jsonify({"status": "requested"})

@self.app.route("/api/mobile/pairing/pending", methods=["GET"])
def pairing_pending():
    """PC 端轮询是否有待确认的配对请求"""
    pending = server._pairing.get_pending()
    if pending is None:
        return jsonify({"status": "none"})
    return jsonify({
        "status": "pending",
        "device_name": pending.device_name,
        "requested_at": pending.requested_at,
    })

@self.app.route("/api/mobile/pairing/confirm", methods=["POST"])
def pairing_confirm():
    """PC 端确认配对 → 生成配对码"""
    if server._pairing.get_pending() is None:
        return jsonify({"error": "没有待确认的配对请求"}), 404
    code = server._pairing.confirm_pending()
    return jsonify({
        "status": "confirmed",
        "pairing_code": code,
        "expires_in": PAIRING_CODE_TTL,
    })

@self.app.route("/api/mobile/pairing/reject", methods=["POST"])
def pairing_reject():
    """PC 端拒绝配对"""
    server._pairing.reject_pending()
    return jsonify({"status": "rejected"})

@self.app.route("/api/mobile/pairing/submit-code", methods=["POST"])
def pairing_submit_code():
    """手机端提交配对码"""
    data = request.get_json(force=True, silent=True) or {}
    code = data.get("code", "")
    device_name = data.get("device_name", "")
    
    if not server._pairing.verify_code(code.upper()):
        return jsonify({"status": "invalid", "error": "配对码错误或已过期"}), 400
    
    # 验证成功 → 生成 token
    server._pairing.consume_code()
    token = server._token_mgr.generate_token(device_name)
    server._pairing.clear_pending()
    
    # 停止配对模式（配对完成）
    server.stop_pairing_mode()
    
    return jsonify({"status": "paired", "token": token})
```

### 3.2 主 Flask 桥接端点（端口 5000）

在 `backend/api_server.py` 新增：

```python
# ============== 配对模式管理 ==============

@app.route('/api/mobile/pairing/start', methods=['POST'])
def mobile_pairing_start():
    """开启配对模式（启动 mDNS 广播）"""
    try:
        server = _get_mobile_server()
        if server is None:
            return jsonify({'error': '移动接入服务未启动'}), 400
        result = server.start_pairing_mode()
        return jsonify(result)
    except Exception as e:
        logger.error(f'[API] 开启配对模式失败: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/mobile/pairing/stop', methods=['POST'])
def mobile_pairing_stop():
    """停止配对模式"""
    try:
        server = _get_mobile_server()
        if server:
            server.stop_pairing_mode()
        return jsonify({'status': 'stopped'})
    except Exception as e:
        logger.error(f'[API] 停止配对模式失败: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/mobile/pairing/pending', methods=['GET'])
def mobile_pairing_pending():
    """PC 端轮询待确认配对请求"""
    try:
        server = _get_mobile_server()
        if server is None:
            return jsonify({'status': 'none'})
        # 直接调用移动服务的方法
        pending = server._pairing.get_pending()
        if pending is None:
            return jsonify({'status': 'none'})
        return jsonify({
            'status': 'pending',
            'device_name': pending.device_name,
            'requested_at': pending.requested_at,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mobile/pairing/confirm', methods=['POST'])
def mobile_pairing_confirm():
    """PC 端确认配对 → 返回配对码"""
    try:
        server = _get_mobile_server()
        if server is None:
            return jsonify({'error': '移动接入服务未启动'}), 400
        code = server._pairing.confirm_pending()
        return jsonify({
            'status': 'confirmed',
            'pairing_code': code,
            'expires_in': 120,
        })
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mobile/pairing/reject', methods=['POST'])
def mobile_pairing_reject():
    """PC 端拒绝配对"""
    try:
        server = _get_mobile_server()
        if server:
            server._pairing.reject_pending()
        return jsonify({'status': 'rejected'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## Phase 4 — PC 前端 MobileDeviceManager 重设计

> 目标：将现有单开关 + 二维码面板，改为「总开关」+「配对模式开关」双开关布局，支持配对三状态弹窗。

### 4.1 组件结构改造

```
MobileDeviceManager.tsx
├── 总开关区域（移动接入服务 开/关）
├── 配对模式区域（点击开启 → 弹出配对状态弹窗）
├── 已配对设备列表
└── 配对状态弹窗（三状态）
    ├── 状态 A：广播中（显示 IP/端口 + 停止按钮）
    ├── 状态 B：收到配对请求（确认/拒绝）
    └── 状态 C：显示配对码（120 秒倒计时）
```

### 4.2 关键状态设计

```typescript
type PairingState = 'idle' | 'broadcasting' | 'request_received' | 'show_code';

const [pairingState, setPairingState] = useState<PairingState>('idle');
const [pendingDevice, setPendingDevice] = useState<string>('');
const [pairingCode, setPairingCode] = useState<string>('');
const [codeCountdown, setCodeCountdown] = useState<number>(120);
```

### 4.3 轮询待确认请求

```typescript
// 开启配对模式后，每 2 秒轮询一次
useEffect(() => {
  if (pairingState !== 'broadcasting') return;
  
  const interval = setInterval(async () => {
    const res = await api.getPairingPending();
    if (res.status === 'pending') {
      setPendingDevice(res.device_name);
      setPairingState('request_received');
    }
  }, 2000);
  
  return () => clearInterval(interval);
}, [pairingState]);
```

### 4.4 确认配对 → 显示配对码

```typescript
const handleConfirmPairing = async () => {
  const res = await api.confirmPairing();
  setPairingCode(res.pairing_code);
  setPairingState('show_code');
  setCodeCountdown(120);
  
  // 倒计时
  const timer = setInterval(() => {
    setCodeCountdown(prev => {
      if (prev <= 1) {
        clearInterval(timer);
        setPairingState('idle');
        return 0;
      }
      return prev - 1;
    });
  }, 1000);
};
```

### 4.5 i18n 新增字符串

在 `I18nContext.tsx` 中新增：

```typescript
pairing: {
  title: '配对模式',
  description: '开启后广播服务，允许新设备配对',
  start: '点击开启',
  stop: '停止广播',
  broadcasting: '正在广播...',
  deviceFound: '等待设备连接...',
  confirmPairing: '确认配对',
  rejectPairing: '拒绝',
  pairingCode: '配对码',
  enterCodeOnPhone: '请在手机上输入此配对码',
  codeExpiresIn: '有效期: {seconds} 秒',
  cancelPairing: '取消配对',
  requestFrom: '{device} 请求配对',
},
```

---

## Phase 5 — Flutter 连接页 mDNS 发现重写

> 目标：将 `connect_screen.dart` 从手动输入 IP/端口，重写为 mDNS 自动发现。

### 5.1 新增 `lib/services/mdns_discovery.dart`

```dart
import 'dart:async';
import 'package:multicast_dns/multicast_dns.dart';

class DiscoveredService {
  final String name;
  final String host;
  final int port;

  DiscoveredService({required this.name, required this.host, required this.port});

  @override
  String toString() => '$name @ $host:$port';
}

class MdnsDiscovery {
  static const String _serviceType = '_blurarc._tcp.local.';
  MDnsClient? _client;

  Stream<DiscoveredService> discover({
    Duration timeout = const Duration(seconds: 5),
  }) async* {
    _client = MDnsClient();
    await _client!.start();

    await for (final PtrRecord ptr in _client!.lookup<PtrRecord>(
      PtrRecord.query(_serviceType),
      timeout: timeout,
    )) {
      await for (final SrvRecord srv in _client!.lookup<SrvRecord>(
        SrvRecord.query(ptr.domainName),
        timeout: const Duration(seconds: 2),
      )) {
        await for (final IPAddressRecord ip in _client!.lookup<IPAddressRecord>(
          ResourceRecordQuery.addressIPv4(srv.target),
          timeout: const Duration(seconds: 2),
        )) {
          yield DiscoveredService(
            name: ptr.domainName.replaceAll('.$_serviceType', ''),
            host: ip.addresses.first.address,
            port: srv.port,
          );
        }
      }
    }

    _client?.stop();
    _client = null;
  }

  void dispose() {
    _client?.stop();
    _client = null;
  }
}
```

### 5.2 重写 `connect_screen.dart`

新交互流程：
1. 进入页面立即开始 mDNS 扫描
2. 显示发现的 PC 列表（卡片：电脑名 + IP:端口）
3. 点击卡片 → 发送配对请求 → 跳转到配对码输入页
4. 支持手动输入 IP（备选）

```dart
class ConnectScreen extends StatefulWidget {
  @override
  _ConnectScreenState createState() => _ConnectScreenState();
}

class _ConnectScreenState extends State<ConnectScreen> {
  final _mdns = MdnsDiscovery();
  final _discovered = <DiscoveredService>[];
  bool _isScanning = true;

  @override
  void initState() {
    super.initState();
    _startDiscovery();
  }

  void _startDiscovery() async {
    setState(() => _isScanning = true);
    _discovered.clear();

    await for (final service in _mdns.discover()) {
      setState(() {
        _discovered.add(service);
      });
    }

    setState(() => _isScanning = false);
  }

  void _onDeviceTap(DiscoveredService service) async {
    // 发送配对请求
    final api = ApiClient();
    api.setConnectionParams(service.host, service.port);
    await api.pairingRequest('My Phone');  // device_name 可让用户输入
    // 跳转到配对码输入页
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => PairingCodeScreen(
          api: api,
          deviceName: 'My Phone',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(t.connectToPc),
        actions: [
          IconButton(icon: Icon(Icons.refresh), onPressed: _startDiscovery),
        ],
      ),
      body: _isScanning && _discovered.isEmpty
          ? Center(child: CircularProgressIndicator())
          : _discovered.isEmpty
              ? _buildEmptyState()
              : _buildDeviceList(),
    );
  }
}
```

---

## Phase 6 — Flutter 配对码输入页

> 目标：手机端输入 6 位配对码，提交后获取 token。

### 6.1 新增 `lib/screens/pairing_code_screen.dart`

```dart
class PairingCodeScreen extends StatefulWidget {
  final ApiClient api;
  final String deviceName;

  const PairingCodeScreen({
    required this.api,
    required this.deviceName,
  });

  @override
  _PairingCodeScreenState createState() => _PairingCodeScreenState();
}

class _PairingCodeScreenState extends State<PairingCodeScreen> {
  final _codeControllers = List.generate(6, (_) => TextEditingController());
  final _focusNodes = List.generate(6, (_) => FocusNode());
  bool _isSubmitting = false;
  String? _error;

  String get _code => _codeControllers.map((c) => c.text).join();

  void _submitCode() async {
    if (_code.length != 6) return;

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      final token = await widget.api.submitPairingCode(_code, widget.deviceName);
      if (token != null) {
        // 保存连接信息
        await widget.api.saveConnection(
          widget.api.baseUrl,
          token,
        );
        // 跳转到首页
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => AlbumScreen()),
          (route) => false,
        );
      } else {
        setState(() => _error = t.pairingCodeInvalid);
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(t.enterPairingCode)),
      body: Padding(
        padding: EdgeInsets.all(24),
        child: Column(
          children: [
            Text(t.pairingCodeHint, style: Theme.of(context).textTheme.bodyLarge),
            SizedBox(height: 32),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(6, (i) => Container(
                width: 48,
                margin: EdgeInsets.symmetric(horizontal: 4),
                child: TextField(
                  controller: _codeControllers[i],
                  focusNode: _focusNodes[i],
                  textAlign: TextAlign.center,
                  maxLength: 1,
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                  onChanged: (v) {
                    if (v.isNotEmpty && i < 5) {
                      _focusNodes[i + 1].requestFocus();
                    }
                    if (_code.length == 6) _submitCode();
                  },
                  decoration: InputDecoration(counterText: ''),
                ),
              )),
            ),
            if (_error != null) ...[
              SizedBox(height: 16),
              Text(_error!, style: TextStyle(color: Colors.red)),
            ],
            SizedBox(height: 32),
            ElevatedButton(
              onPressed: _isSubmitting ? null : _submitCode,
              child: _isSubmitting
                  ? CircularProgressIndicator()
                  : Text(t.confirmPairing),
            ),
          ],
        ),
      ),
    );
  }
}
```

### 6.2 `api_client.dart` 新增方法

```dart
/// 发起配对请求
Future<void> pairingRequest(String deviceName) async {
  final res = await _dio.post(
    '$baseUrl/api/mobile/pairing/request',
    data: {'device_name': deviceName},
  );
  if (res.statusCode != 200) throw Exception(t.pairingRequestFailed);
}

/// 提交配对码
Future<String?> submitPairingCode(String code, String deviceName) async {
  final res = await _dio.post(
    '$baseUrl/api/mobile/pairing/submit-code',
    data: {'code': code, 'device_name': deviceName},
  );
  final data = res.data as Map<String, dynamic>;
  if (data['status'] == 'paired') {
    return data['token'] as String;
  }
  return null;
}
```

---

## Phase 7 — Flutter 首页三 Tab 重设计

> 目标：将现有单页面改为底部三 Tab（相册/上传/设置）。

### 7.1 修改 `lib/app.dart` 或 `lib/main.dart`

使用 `StatefulShellRoute`（go_router）或简单的 `StatefulWidget` + `BottomNavigationBar`：

```dart
class HomePage extends StatefulWidget {
  @override
  _HomePageState createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _currentIndex = 0;

  final _pages = [
    AlbumTab(),      // 🖼 相册
    UploadTab(),     // 📤 上传
    SettingsTab(),   // ⚙️ 设置
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (i) => setState(() => _currentIndex = i),
        selectedItemColor: Color(0xFF22D3EE),
        items: [
          BottomNavigationBarItem(icon: Icon(Icons.photo), label: t.album),
          BottomNavigationBarItem(icon: Icon(Icons.upload), label: t.upload),
          BottomNavigationBarItem(icon: Icon(Icons.settings), label: t.settings),
        ],
      ),
    );
  }
}
```

### 7.2 相册 Tab — 瀑布流按目录分组

新增 `lib/widgets/photo_waterfall.dart`：

```dart
class PhotoWaterfall extends StatefulWidget {
  @override
  _PhotoWaterfallState createState() => _PhotoWaterfallState();
}

class _PhotoWaterfallState extends State<PhotoWaterfall> {
  final _groups = <PhotoGroup>[];  // [{dirName, photos, dateLabel}]
  int _currentPage = 0;
  bool _isLoading = false;
  bool _hasMore = true;

  @override
  void initState() {
    super.initState();
    _loadMore();
  }

  void _loadMore() async {
    if (_isLoading || !_hasMore) return;
    setState(() => _isLoading = true);

    final photos = await ApiClient().getPhotos(page: _currentPage, pageSize: 60);
    if (photos.isEmpty) {
      setState(() => _hasMore = false);
    } else {
      // 按目录分组
      _groupPhotos(photos);
      setState(() {
        _currentPage++;
        _isLoading = false;
      });
    }
  }

  String _formatGroupLabel(String dirPath) {
    // 尝试解析为 YYYY年M月 格式
    final name = dirPath.split('/').last;
    final match = RegExp(r'^(\d{4})-(\d{2})$').firstMatch(name);
    if (match != null) {
      final year = match.group(1)!;
      final month = int.parse(match.group(2)!);
      return '${year}年${month}月';
    }
    return name;  // 非年月格式直接显示目录名
  }

  @override
  Widget build(BuildContext context) {
    return NotificationListener<ScrollNotification>(
      onNotification: (scroll) {
        if (scroll.metrics.pixels >= scroll.metrics.maxExtent - 200) {
          _loadMore();
        }
        return false;
      },
      child: ListView.builder(
        itemCount: _groups.length + 1,
        itemBuilder: (ctx, i) {
          if (i == _groups.length) {
            return _isLoading
                ? Center(child: CircularProgressIndicator())
                : SizedBox.shrink();
          }
          final group = _groups[i];
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Text(
                  '── ${group.label} ──',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              GridView.builder(
                shrinkWrap: true,
                physics: NeverScrollableScrollPhysics(),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 3,
                  childAspectRatio: 1,
                ),
                itemCount: group.photos.length,
                itemBuilder: (ctx, j) => PhotoCard(photo: group.photos[j]),
              ),
            ],
          );
        },
      ),
    );
  }
}
```

### 7.3 设置 Tab

```dart
class SettingsTab extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        SectionHeader(t.appearance),
        ThemeSelector(),  // [暗色 | 亮色 | 跟随系统]
        SectionHeader(t.connection),
        ListTile(
          leading: Icon(Icons.wifi),
          title: Text(t.currentConnection),
          subtitle: Text('${ApiClient().baseUrl}'),
        ),
        ListTile(
          leading: Icon(Icons.refresh),
          title: Text(t.repair),
          onTap: () => _showRepairDialog(context),
        ),
        SectionHeader(t.about),
        ListTile(title: Text('Blur Arc v1.0.0')),
      ],
    );
  }
}
```

---

## Phase 8 — 测试

### 8.1 单元测试

| 测试文件 | 覆盖内容 |
|---------|---------|
| `test_zeroconf_publisher.py` | 启动/停止、重复启动无异常 |
| `test_pairing_manager.py` | 配对码生成/验证/过期/待确认流程 |
| `test_mobile_access_server_pairing.py` | 新增配对端点的集成测试 |

### 8.2 集成测试

```python
def test_full_pairing_flow():
    """完整配对流程测试"""
    server = MobileAccessServer()
    server.start()
    
    # 1. 开启配对模式
    server.start_pairing_mode()
    assert server._zeroconf is not None
    
    # 2. 模拟手机端发起配对请求
    with server.app.test_client() as c:
        res = c.post('/api/mobile/pairing/request', json={'device_name': 'Test Phone'})
        assert res.status_code == 200
        
        # 3. PC 端确认
        res = c.post('/api/mobile/pairing/confirm')
        data = json.loads(res.data)
        assert data['status'] == 'confirmed'
        code = data['pairing_code']
        
        # 4. 手机端提交配对码
        res = c.post('/api/mobile/pairing/submit-code', 
                      json={'code': code, 'device_name': 'Test Phone'})
        data = json.loads(res.data)
        assert data['status'] == 'paired'
        assert 'token' in data
        
        # 5. 验证 token 可用
        res = c.get('/api/mobile/verify', 
                     headers={'Authorization': f'Bearer {data["token"]}'})
        assert res.status_code == 200
    
    server.stop_pairing_mode()
    server.stop()
```

### 8.3 Flutter 测试

```dart
// flutter_app/test/mdns_discovery_test.dart
void main() {
  test('MdnsDiscovery parses service records', () async {
    // 使用 mock MDnsClient 测试
  });
}
```

---

## 实施顺序与依赖

```
Phase 1 (ZeroconfPublisher)
   │
   ▼
Phase 2 (PairingManager)
   │
   ▼
Phase 3 (API 端点) ───── 可并行 ──── Phase 5 (Flutter mDNS 发现)
   │                                      │
   ▼                                      ▼
Phase 4 (PC 前端)                    Phase 6 (配对码输入页)
   │                                      │
   ▼                                      ▼
               Phase 7 (Flutter 三 Tab)
                        │
                        ▼
                   Phase 8 (测试)
```

**可并行路径：**
- 路径 A：Phase 1 → 2 → 3 → 4（后端 + PC 前端）
- 路径 B：Phase 5 → 6 → 7（Flutter 端）
- 两条路径在 Phase 3 API 定义对齐后即可并行

---

## 与现有代码的兼容

- **保留**：`TokenManager`、`MobileAccessServer` 核心、所有资源端点（`/tree`、`/photos` 等）
- **改造**：`connect_screen.dart` 完全重写；`MobileDeviceManager.tsx` 大幅改造
- **新增**：`ZeroconfPublisher`、`PairingManager`、Flutter `MdnsDiscovery`
- **向后兼容**：旧版 Flutter App（手动输入 IP）仍可通过 `/pair` 端点配对（保留兼容性，标记为 deprecated）

---

## 完成标准

- [ ] `pytest test/unit/test_zeroconf_publisher.py test_pairing_manager.py -v` 全部 PASS
- [ ] `flutter analyze` 无 error（允许 info 级别警告）
- [ ] TypeScript `npx tsc --noEmit` 无错误
- [ ] 手动测试：手机自动发现 PC → 配对 → 进入相册，全流程通畅
- [ ] 更新 `AGENTS.md` 开发日志
- [ ] 更新 `CLAUDE.md`（如有约定变更）
- [ ] 更新 `.workbuddy/memory/MEMORY.md`
