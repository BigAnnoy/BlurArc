# 2026-06-22: mDNS 广播修复

## 问题

手机端 mDNS 自动发现一直不工作，始终显示"未找到 Blur Arc 服务"。

## 排查过程

### 调用链追踪

```
BlurArc.py: _start_mobile_service()
  └─ server.start()                          # 启动 HTTP 服务
  └─ server.start_pairing_mode()            # ← 之前缺失！
       └─ ZeroconfPublisher(port).start()
            └─ _run() 线程:
                 └─ ServiceInfo(...)         # ← 构造失败！
                 └─ Zeroconf().register_service()
```

### 根因 1：自动启动时未调用 start_pairing_mode()

`_start_mobile_service()` 只调了 `server.start()`，没有调 `server.start_pairing_mode()`，导致 mDNS 广播从未启动。用户必须手动打开"移动设备管理"对话框点击"开始配对"才会触发广播。

**修复：** `BlurArc.py` 第 295 行，`server.start()` 后追加 `server.start_pairing_mode()`。

### 根因 2：ServiceInfo 参数顺序错误（致命）

`zeroconf` 从 0.132+ 重构了 `ServiceInfo` 构造函数签名：

```python
# 当前签名 (zeroconf 0.149.16)
def __init__(
    self,
    type_: str,
    name: str,
    port: int | None = None,       # 位置参数 #3
    weight: int = 0,
    priority: int = 0,
    properties: bytes | dict = b"",
    server: str | None = None,
    host_ttl: int = _DNS_HOST_TTL,
    other_ttl: int = _DNS_OTHER_TTL,
    *,
    addresses: list[bytes] | None = None,    # keyword-only！
    parsed_addresses: list[str] | None = None,
    interface_index: int | None = None,
) -> None:
```

旧代码把 `addresses` 作为位置参数传递，恰好落在 `port` 位置：

```python
# ❌ 旧代码
ServiceInfo(
    SERVICE_TYPE,                    # → type_ ✅
    name,                            # → name ✅
    addresses=[address],             # → port ❌ (被当作 port 的值)
    port=self.port,                  # → port ❌ TypeError: multiple values for 'port'
    properties={...},
)
```

`addresses` 是 keyword-only 参数，不能作为位置参数传递。这导致 `TypeError: got multiple values for argument 'port'`，线程静默失败，后台日志只有 `[Zeroconf] 启动失败: ...`。

**修复：** 调换 `port` 和 `addresses` 的顺序，让 `port` 作为位置参数 #3，`addresses` 作为 keyword 参数。

```python
# ✅ 修复后
ServiceInfo(
    SERVICE_TYPE,
    name,
    port=self.port,                  # → port ✅
    addresses=[address],             # → addresses ✅ (keyword)
    properties={...},
)
```

## 改动文件

| 文件 | 改动 |
|------|------|
| `backend/zeroconf_publisher.py` | 修复 `ServiceInfo` 参数顺序；新增 `_ready` 事件 + `wait_ready()` + `_last_error`；`is_running()` 增加 `_ready.is_set()` 检查 |
| `backend/mobile_access_server.py` | `start_pairing_mode()` 调用 `wait_ready()`，返回 `mDNS_ready` 字段 |
| `src/BlurArc.py` | `_start_mobile_service()` 追加 `start_pairing_mode()` 调用，并检查 `mDNS_ready` 结果 |

## 验证

```bash
$ python -c "from backend.zeroconf_publisher import ZeroconfPublisher; \
  p = ZeroconfPublisher(8900); p.start(); ok = p.wait_ready(3.0); \
  print('mDNS ready:', ok, '| error:', p._last_error); p.stop()"

mDNS ready: True | error: None
```

## 注意事项

- **Android 模拟器不支持组播**（NAT 隔离），mDNS 自动发现只能在真机测试
- 模拟器可通过手动输入 `10.0.2.2:8900` 测试配对流程
- Windows 防火墙可能拦截 mDNS（端口 5353 UDP），如果真机也发现不了，检查防火墙设置