# 手机配对与发现流程重设计

> 版本: v1.2 | 日期: 2026-06-18 | 状态: 待评审
> v1.2 更新: 首页改为三个 Tab（相册/上传/设置），相册瀑布流按目录分组
> v1.1 更新: 首页底部改为双 Tab（首页/设置），设置页包含主题切换和重新配对

---

## 1. 概述

### 1.1 动机

当前移动接入的配对流程需要用户手动输入电脑 IP 和端口，或扫码连接，操作门槛较高。用户希望实现**零配置发现**：手机端自动搜索局域网内的 PC 端服务，点击即连，仅需输入配对码完成授权。

### 1.2 目标

- PC 端开启服务后通过 mDNS 广播自身，手机端自动发现
- 配对流程安全、可控：手机请求 → PC 端确认 → 配对码二次验证
- 支持已配对设备与配对模式分离管理

### 1.3 非目标

- 不涉及互联网远程访问（纯局域网）
- 不做自动重连 / 后台保活

---

## 2. 用户流程

```
  ┌─────────────────┐           ┌─────────────────┐
  │  PC 端           │           │  手机端          │
  └─────────────────┘           └─────────────────┘
          │                            │
  ① 开启移动接入总开关                    │
  ② 点击「配对模式」                       │
     → mDNS 广播开始                     │
     → 显示 IP/端口/等待中                │
          │                            │
          │◄──── ③ 手机搜索到 PC ────────│
          │                            │  自动扫描 mDNS
          │                            │  显示 PC 列表
          │                            │  用户点击 PC
          │◄──── ④ 发起配对请求 ─────────│
          │                            │
  ⑤ 弹出确认框                           │
     「Pixel 8 请求配对」                  │
     用户点击[确认]                       │
          │                            │
  ⑥ 弹出配对码小窗                        │
     XD4K9M (120秒有效)                 │
          │                            │
          │◄──── ⑦ 输入配对码 ──────────│
          │                            │
  ⑧ 配对完成                             │
     → 关闭配对模式                       │
     → 添加设备到列表                     │
          │──────── 返回 token ────────►│
          │                            │  进入相册首页
```

---

## 3. PC 端设计

### 3.1 手机管理对话框

在现有 `MobileDeviceManager` 组件基础上改造，布局如下：

```
┌──────────────────────────────────────┐
│  📱 移动管理                          │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │  🔘 移动接入服务       [开/关]    │  │  ← 总开关
│  │  已配对 2 台，已连接 0 台         │  │
│  └─────────────────────────────────┘  │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │  🔘 配对模式          [点击开启] │  │  ← 配对开关
│  │  开启后广播服务，允许新设备配对   │  │
│  └─────────────────────────────────┘  │
│                                       │
│  ── 已配对设备 ──                      │
│  ┌──────────────────────────────┐     │
│  │ 📱 Pixel 8        [断开]     │     │
│  │    最后访问: 10分钟前         │     │
│  ├──────────────────────────────┤     │
│  │ 📱 iPhone 15     [断开]      │     │
│  │    最后访问: 2小时前          │     │
│  └──────────────────────────────┘     │
└──────────────────────────────────────┘
```

### 3.2 配对流程的三个子状态

**状态 A — 广播中：**

```
┌────────────────────────────────────┐
│  📡 正在广播...                     │
│                                     │
│  电脑: BIGANNOY-DESKTOP             │
│  IP:   192.168.31.164:8900         │
│                                     │
│  等待设备连接...                     │
│  [停止广播]                         │
└────────────────────────────────────┘
```

**状态 B — 收到配对请求：**

```
┌────────────────────────────────────┐
│  📱 请求配对                        │
│                                     │
│  设备: Pixel 8                      │
│                                     │
│  ┌────────────┐  ┌────────────┐    │
│  │  确认      │  │  拒绝      │    │
│  └────────────┘  └────────────┘    │
└────────────────────────────────────┘
```

**状态 C — 显示配对码：**

```
┌────────────────────────────────────┐
│  🔑 配对码                          │
│                                     │
│       X D 4 K 9 M                  │
│                                     │
│  请在手机上输入此配对码               │
│  有效期: 120 秒                     │
│  [取消配对]                         │
└────────────────────────────────────┘
```

### 3.3 后端新增 mDNS 广播

`backend/mobile_access_server.py` 新增 mDNS 广播能力：

```python
class ZeroconfPublisher:
    """mDNS 服务广播"""

    SERVICE_TYPE = "_blurarc._tcp.local."
    SERVICE_NAME = "Blur Arc on {hostname}.{type}"

    def __init__(self, port: int):
        self.port = port
        self._zc: Zeroconf | None = None

    def start(self):
        """开始广播"""
        props = {"service": "Blur Arc Mobile Access", "version": "1.0"}
        info = ServiceInfo(
            SERVICE_TYPE,
            SERVICE_NAME.format(hostname=socket.gethostname(), type=SERVICE_TYPE),
            addresses=[socket.inet_aton(_get_local_ip())],
            port=self.port,
            properties=props,
        )
        self._zc = Zeroconf()
        self._zc.register_service(info)

    def stop(self):
        """停止广播"""
        if self._zc:
            self._zc.unregister_all_services()
            self._zc.close()
```

新增依赖：`zeroconf>=0.132.0`

### 3.4 配对码逻辑

```python
import secrets
import string

class PairingManager:
    CODE_LENGTH = 6
    CODE_TTL = 120  # 秒

    def __init__(self):
        self._current_code: str | None = None
        self._code_expires_at: float = 0
        self._pending_device: dict | None = None

    def generate_code(self) -> str:
        self._current_code = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits)
            for _ in range(self.CODE_LENGTH)
        )
        self._code_expires_at = time.time() + self.CODE_TTL
        return self._current_code

    def verify_code(self, code: str) -> bool:
        if time.time() > self._code_expires_at:
            return False
        return secrets.compare_digest(self._current_code or "", code)

    def set_pending_device(self, device_name: str):
        self._pending_device = {"device_name": device_name}

    def consume_pending(self) -> dict | None:
        d = self._pending_device
        self._pending_device = None
        return d
```

### 3.5 TokenManager 新增

复用现有 `TokenManager`（`mobile_access_server.py`），无需大改。配对流程变化在控制层。

---

## 4. 手机端设计

### 4.1 连接页 — 设备发现

```
┌──────────────────────────────┐
│  🔍 搜索局域网中的电脑...       │
│                              │
│  ┌──────────────────────────┐│
│  │ 🖥  BIGANNOY-DESKTOP     ││  ← 点击进入配对码输入
│  │    192.168.31.164:8900   ││
│  └──────────────────────────┘│
│                              │
│  [🔄 刷新]  [⌨️ 手动输入]     │
└──────────────────────────────┘
```

**页面行为：**
- 进入页面立即开始 mDNS 扫描
- 实时显示发现的 PC（服务类型 `_blurarc._tcp.local.`）
- 每 3 秒刷新一次
- 无发现时显示"搜索中…"动画
- 支持下拉刷新

### 4.2 配对码输入页

```
┌──────────────────────────────┐
│  🔑 输入配对码                 │
│                              │
│  电脑: BIGANNOY-DESKTOP      │
│  IP: 192.168.31.164          │
│                              │
│  ┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐  │
│  │  ││  ││  ││  ││  ││  │  │  ← 6 位独立输入框
│  └──┘└──┘└──┘└──┘└──┘└──┘  │
│                              │
│  [确认配对]                    │
│  [返回]                      │
└──────────────────────────────┘
```

### 4.3 首页（配对后）

配对成功后进入，底部三个 Tab。

#### 底部 TabBar

```
┌──────────────────────────────┐
│                              │
│         (页面内容)            │
│                              │
│                              │
├──────────────────────────────┤
│  🖼 相册 │ 📤 上传 │ ⚙️ 设置│  ← 底部 TabBar
└──────────────────────────────┘
```

三个 Tab 切换平滑，当前 Tab 高亮为主色 `#22D3EE`。

---

#### 🖼 相册 Tab（默认首页）

默认展示瀑布流无限滚动，照片按 PC 端目录顺序分组，分隔线使用中文年月格式。

```
┌──────────────────────────────┐
│  🖼  相册          [📂 目录] │  ← 📂 次要入口，点击进入目录树
├──────────────────────────────┤
│                              │
│  ── 2025年6月 ──              │  ← 分隔线（YYYY年M月）
│  ┌────┐ ┌────┐ ┌────┐       │
│  │ 📷 │ │ 📷 │ │ 📷 │       │
│  └────┘ └────┘ └────┘       │
│  ┌────┐ ┌────┐              │
│  │ 📷 │ │ 📷 │              │
│  └────┘ └────┘              │
│                              │
│  ── 2025年5月 ──              │
│  ┌────┐ ┌────┐ ┌────┐ ┌───┐│
│  │ 📷 │ │ 📷 │ │ 📷 │ │ 📷││
│  └────┘ └────┘ └────┘ └───┘│
│                              │
│  ── Screenshots ──            │  ← 非年月目录直接显示目录名
│  ┌────┐ ┌────┐ ┌────┐       │
│  │ 📷 │ │ 📷 │ │ 📷 │       │
│  └────┘ └────┘ └────┘       │
│                              │
│  ── 加载中... ──              │  ← 滚动到底自动加载更多
│                              │
├──────────────────────────────┤
│  🖼 相册 │ 📤 上传 │ ⚙️ 设置│
└──────────────────────────────┘
```

**交互细节：**
- 进入 App 默认显示相册 Tab，直接展示照片网格
- 往下滚动自动加载更早目录的照片（无限滚动）
- 分隔线格式：YYYY年M月（如 `2025年6月`），非年月格式目录直接显示目录名
- 右上角 📂 图标点击进入目录树视图（层级列表，点击目录进入照片网格）
- 点击任意照片 → 全屏预览（左右滑动翻页）
- 照片网格 3 列，缩略图正方形裁切

---

#### 📤 上传 Tab

```
┌──────────────────────────────┐
│  📤  上传到相册               │
├──────────────────────────────┤
│                              │
│  目标: BIGANNOY-DESKTOP      │
│                              │
│  ┌──────────────────────────┐│
│  │    📷                     ││
│  │   选择照片或视频          ││
│  │   点击从本机选择          ││
│  └──────────────────────────┘│
│                              │
│  ── 已选择 (3) ──            │
│                              │
│  ┌────┐ ┌────┐ ┌────┐       │
│  │ 📷 │ │ 📷 │ │ 📷 │       │
│  └────┘ └────┘ └────┘       │
│                              │
│  共 15.2 MB                  │
│                              │
│  ┌──────────────────────────┐│
│  │  上传到相册               ││
│  └──────────────────────────┘│
│                              │
├──────────────────────────────┤
│  🖼 相册 │ 📤 上传 │ ⚙️ 设置│
└──────────────────────────────┘
```

---

#### ⚙️ 设置 Tab

```
┌──────────────────────────────┐
│  ⚙️  设置                    │
├──────────────────────────────┤
│                              │
│  ── 外观 ──                   │
│                              │
│  🎨 主题                     │
│  [🌙 暗色 | ☀️ 亮色 | 📱 跟随系统]│
│                              │
│  ── 连接 ──                   │
│                              │
│  📡 当前连接                  │
│  BIGANNOY-DESKTOP            │
│  192.168.31.164:8900         │
│                              │
│  ┌──────────────────────────┐│
│  │ 🔄 重新配对               ││
│  └──────────────────────────┘│
│                              │
│  ── 关于 ──                   │
│  Blur Arc v1.0.0             │
│                              │
├──────────────────────────────┤
│  🖼 相册 │ 📤 上传 │ ⚙️ 设置│
└──────────────────────────────┘
```

**交互细节：**
- 「主题」切换后立即生效，通过 Flutter 的 ThemeMode 控制
- 跟随系统模式监听 `MediaQuery.platformBrightness`
- 「当前连接」仅展示信息，不可操作
- 「重新配对」点击后弹出确认对话框：「确定断开当前连接并重新配对吗？」，确认后清除 token 回到发现页

---

## 5. 关键交互细节

| 步骤 | 用户操作 | 系统响应 |
|------|---------|---------|
| 开启配对 | 点击「配对模式」 | 弹出广播小窗，开始 mDNS 广播 |
| 手机发现 PC | 进入手机连接页 | 自动扫描，列表显示 PC 名称/IP |
| 选择 PC | 点击 PC 卡片 | 跳转到配对码输入页 |
| 发起配对 | 手机端发送配对请求 | PC 端弹出「XX 请求配对」确认框 |
| 确认配对 | PC 端点击确认 | 弹出配对码小窗 |
| 输入配对码 | 手机端输入 6 位码 | PC 端验证 → 返回 token → 关闭配对模式 |
| 断开设备 | PC 端点击「断开」 | 撤销该设备 token，设备下次请求 401 |
| 关闭总开关 | 关闭「移动接入服务」 | 停止服务，所有设备 token 失效 |
| 手机断开 | 手机端点击「断开」 | 清除本地 token 存储，回到发现页 |

---

## 6. 移动端 mDNS 发现实现

### 6.1 Dart 端使用 `multicast_dns` 包

```dart
import 'package:multicast_dns/multicast_dns.dart';

class MdnsDiscovery {
  MDnsClient? _client;
  
  Stream<DiscoveredService> discover({Duration timeout = const Duration(seconds: 5)}) async* {
    _client = MDnsClient();
    await _client!.start();
    
    await for (final service in _client!.lookup<ServiceRecord>(
      type: '_blurarc._tcp.local.',
      timeout: timeout,
    )) {
      final ip = service.addr?.first;
      if (ip != null) {
        yield DiscoveredService(
          name: service.name.replaceAll('.$type', ''),
          host: ip.address,
          port: service.port,
        );
      }
    }
    
    _client!.stop();
  }
  
  void dispose() {
    _client?.stop();
  }
}
```

`pubspec.yaml` 已有 `multicast_dns: ^0.3.2`，直接复用。

---

## 7. API 变更

### 新增端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/mobile/pairing/start` | 开始配对模式（开启广播，生成待确认状态） |
| POST | `/api/mobile/pairing/stop` | 停止配对模式 |
| GET | `/api/mobile/pairing/pending` | PC 端轮询是否有待确认的配对请求 |
| POST | `/api/mobile/pairing/confirm` | PC 端确认配对请求 → 返回配对码 |
| POST | `/api/mobile/pairing/reject` | PC 端拒绝配对请求 |
| POST | `/api/mobile/pairing/submit-code` | 手机端提交配对码（替代原 pair-request） |

### 端点详情

**`POST /api/mobile/pairing/start`**
```
请求: {}
响应: {"status": "broadcasting", "hostname": "BIGANNOY-DESKTOP", "local_ip": "192.168.31.164", "port": 8900}
```

**`POST /api/mobile/pairing/confirm`**
```
请求: {"device_name": "Pixel 8"}
响应: {"status": "confirmed", "pairing_code": "XD4K9M", "expires_in": 120}
```

**`POST /api/mobile/pairing/submit-code`**
```
请求: {"code": "XD4K9M", "device_name": "Pixel 8"}
响应: {"status": "paired", "token": "abc123..."}
```

---

## 8. 安全措施

| 措施 | 说明 |
|------|------|
| 配对码仅限局域网传输 | mDNS + 直连 HTTP，不经过公网 |
| 配对码 TTL 120 秒 | 超时自动失效，需重新生成 |
| 配对确认机制 | 即使知道配对码，也需 PC 端主动确认后才能获取配对码 |
| 速率限制 | 每个 IP 每分钟最多 10 次配对请求 |
| 已配对设备独立 token | 令牌可单独撤销，不影响其他设备 |
| 总开关隔离 | 关闭总开关后所有 token 立即失效 |

---

## 9. 与现有实现的关系

### 保留
- `MobileAccessServer` 核心（端口管理、CORS、token 验证等）
- `TokenManager`（令牌生成、持久化、撤销）
- 所有 `/api/mobile/verify`, `/api/mobile/tree`, `/api/mobile/photos` 等资源端点
- Flutter 端的 ApiClient、相册浏览、上传等功能

### 改造
- `connect_screen.dart`：重写为 mDNS 发现 + 配对码输入
- `MobileDeviceManager.tsx`：改为两个开关 + 配对三状态弹窗

### 新增
- `ZeroconfPublisher`：mDNS 广播类
- `PairingManager`：配对码生成/验证/待确认管理
- Flutter MDnsDiscovery 模块

---

## 10. 测试要点

### 单元测试
- `PairingManager` 配对码生成/验证/过期
- `ZeroconfPublisher` 启动/停止
- mDNS 发现结果解析

### 集成测试
- 完整配对流程：配对模式 → mDNS 发现 → 确认 → 配对码 → token
- 配对码过期重试
- 总开关关闭后已配对设备 401

### 手动测试
- 手机端搜索到 PC 列表（真实 WiFi 环境）
- 配对码输入错误/超时
- 两台 PC 同时广播的场景
