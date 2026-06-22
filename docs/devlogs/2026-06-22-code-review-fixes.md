# 2026-06-22 代码审查 4 项修复

## 背景

针对最近改动（mDNS 广播修复、导入预检去重性能、平板 UI 对齐）进行代码审查，发现 4 个问题并全部修复。

## 修复清单

### 1. `home_page.dart` 断连页溢出保护

**问题：** 平板横屏（1280x800）/ 小屏手机上，`_disconnected` 状态的 `Column` 缺少滚动容器，与之前 `connect_screen` 同款 overflow 风险。

**修复：** 用 `SafeArea + SingleChildScrollView` 包裹 `Center(Column)`，与 `connect_screen._pcOffline` 写法一致。

```dart
// home_page.dart:52-83
body: SafeArea(
  child: SingleChildScrollView(
    padding: const EdgeInsets.all(24),
    child: Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [/* Icon + 文案 + 按钮 */],
      ),
    ),
  ),
),
```

### 2. `api_server.py` 缓存命中时复用 size，去掉 `stat()` I/O

**问题：** `_compute_target_md5` 命中 DB 缓存的 `md5_hash` 时仍调用 `file.stat().st_size`，与"避免 I/O"的优化意图相悖。

**修复：**
- `prescan_index[key]` 改为 `(file, md5_hash, size)` 三元组，把 size 一路带下去
- `_compute_target_md5` 接受 `cached_size`，命中时直接复用（无需 `stat()`）

**效果：** 大规模导入时，每个缓存命中的候选文件省一次 `stat()` 系统调用。

### 3. `api_client.dart` `onDisconnected` 触发条件收敛

**问题：** 任何 `connectionTimeout` / `connectionError` / `sendTimeout` 都会触发 `onDisconnected`，导致：
- 配对阶段首次连接失败时误触发
- 偶发网络抖动导致整个 UI 跳到断连页

**修复：** 新增 `_everConnected` 标志：
- `onResponse` 拦截器：收到 2xx 响应即置为 `true`
- `onError` 拦截器：仅当 `_everConnected=true` 时才触发 `onDisconnected` 并立即重置为 `false`

**效果：** 配对阶段错误不会误断连；已连接后真的断网才会切到断连页。

### 4. `dev-start.bat` 抽取 `:deploy_avd_common` 公共函数

**问题：** `:deploy_emulator` 与 `:deploy_tablet_emulator` 90% 代码重复（仅 AVD 名称 / 标签 / skin 不同）。

**修复：** 抽出 `:deploy_avd_common`，通过 5 个环境变量传参：
- `DEPLOY_AVD_NAME` — AVD 名称
- `DEPLOY_AVD_LABEL` — 日志显示标签（"emulator" / "tablet emulator"）
- `DEPLOY_AVD_SKIN` — 可选 `-skin` 参数（手机 AVD 不传，平板 AVD 传 `1280x800`）
- `DEPLOY_WAIT_LABEL` — `start` 窗口标题
- `DEPLOY_FINISH_MSG` — 结束提示语

调用方简化为 5 行：

```batch
:deploy_emulator
set DEPLOY_AVD_NAME=%AVD_NAME%
set DEPLOY_AVD_LABEL=emulator
set DEPLOY_WAIT_LABEL=Android Emulator
set DEPLOY_FINISH_MSG=Deploy finished!
call :deploy_avd_common
```

**效果：** 文件从 410 行减到 356 行（-54 行），后续新增 AVD 类型只需 5 行。

## 验证

- `flutter analyze lib/screens/home_page.dart lib/services/api_client.dart` → No issues found
- `python -c "import ast; ast.parse(open('backend/api_server.py').read())"` → OK
- `dev-start.bat` 结构 OK，函数调用关系清晰

## 涉及文件

- `blurarc_app/lib/screens/home_page.dart`
- `blurarc_app/lib/services/api_client.dart`
- `backend/api_server.py`
- `scripts/dev-start.bat`
