# 手机端首次连接后照片"加载中"卡死

**日期：** 2026-06-22
**类型：** Bug Fix
**影响范围：** Flutter 手机端（Android）

## 问题现象

手机端连接 PC 后（首次配对或新会话），进入 `AlbumScreen` 一直转圈显示"照片加载中"，无任何错误提示。关掉 App 重新打开后能正常加载。

## 根因分析

### 1. Dio 缺少 `sendTimeout`（主因）

`api_client.dart` 的 `BaseOptions` 只配了 `connectTimeout=5s` 和 `receiveTimeout=10s`，**没有 `sendTimeout`**。

Dio 三个 timeout 含义：

| 字段 | 含义 |
|------|------|
| `connectTimeout` | TCP 握手超时 |
| `sendTimeout` | 等待服务器**返回第一个字节**的超时（请求已发，服务器还没开始响应） |
| `receiveTimeout` | 已开始收字节后，**字节之间**的超时 |

`/api/mobile/photos/sections` 端点先做 SQL 查询再返回 JSON。当 SQLite 首次执行该查询（无查询计划缓存）耗时 > 10s 时：

- `receiveTimeout` 不生效（还没开始收字节）
- `sendTimeout` 是 null → **永远不超时**
- 用户看到的就是"永远在加载"

`api_client.dart:18-22`（修复前）：

```dart
_dio = Dio(BaseOptions(
  connectTimeout: const Duration(seconds: 5),
  receiveTimeout: const Duration(seconds: 10),  // ← 对首字节延迟无效
));
```

### 2. 第二次能成功的原因

- SQLite 编译了查询计划（缓存）
- Flask `threaded=True` 线程池预热
- 网络连接复用（keep-alive）

这些"预热"加起来让第二次请求 < 1s 返回。

### 3. 错误处理 UX 问题（次因）

`AlbumScreen._loadSections` 即使 catch 到异常，也只弹一个 snackbar（[album_screen.dart](file:///f:/AI/Frame_Album/blurarc_app/lib/screens/album_screen.dart)）。在加载阶段网络出错时，用户除了下拉刷新没别的方式重试，且没有明显提示。

## 修复方案

### 修复 #1：Dio 补 `sendTimeout`

[api_client.dart:18-24](file:///f:/AI/Frame_Album/blurarc_app/lib/services/api_client.dart#L18-L24)：

```dart
_dio = Dio(BaseOptions(
  connectTimeout: const Duration(seconds: 5),
  sendTimeout: const Duration(seconds: 30),      // 新增
  receiveTimeout: const Duration(seconds: 30),   // 从 10s 提到 30s
));
```

### 修复 #2：API 调用加 `.timeout(15s)`

[api_client.dart:228-251](file:///f:/AI/Frame_Album/blurarc_app/lib/services/api_client.dart#L228-L251)：

对 `/api/mobile/photos/sections` 和 `/api/mobile/photos/by-month` 显式加客户端 `.timeout(15s)`，比 Dio 的 30s `sendTimeout` 更激进，15s 没收到首字节就主动抛 `TimeoutException`。

### 修复 #3：`AlbumScreen` 错误态 + 重试按钮

- 新增 `_loadError` 状态字段
- catch 时保存错误信息
- build 中显示居中"加载失败"提示 + **"重试"** 按钮
- 区分常见错误：超时 → "网络请求超时，请检查 PC 端是否正常"；连接错误 → "无法连接到 PC，请检查网络"

### 修复 #4：`MonthPhotoScreen` 同样处理

按月份加载的页面也加上重试 UI（[month_photo_screen.dart](file:///f:/AI/Frame_Album/blurarc_app/lib/screens/month_photo_screen.dart)）。

### 修复 #5：服务端 SQL 索引（性能根治）

`photos.media_date` 列没索引。`GROUP BY strftime('%Y-%m', media_date)` 在 20k+ 照片的全表扫描下，首次冷启动很慢。

[database.py:48](file:///f:/AI/Frame_Album/backend/database.py#L48)：

```python
media_date = Column(DateTime(timezone=True), index=True)
```

同时在 [database.py:135-145](file:///f:/AI/Frame_Album/backend/database.py#L135-L145) `init_db()` 加幂等迁移：

```python
conn.execute(text("CREATE INDEX IF NOT EXISTS ix_photos_media_date ON photos (media_date)"))
```

`create_all` 不会给已存在的旧表补索引，必须手动迁移。

## 验证

- `flutter analyze` 三个修改文件 → No issues found
- `python -c "import ast; ast.parse(...)"` 验证 database.py 语法 OK

## 后续可考虑

- 对 `media_date` 加函数索引（`strftime('%Y-%m', media_date)`），SQLite 3.9+ 支持，更进一步优化 GROUP BY
- 监控 `/api/mobile/photos/sections` 的响应时间，>2s 就在服务端 log 警告
