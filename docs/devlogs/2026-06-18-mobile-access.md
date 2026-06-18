# 2026-06-18: 移动接入功能 (Mobile Access)

**计划文档：** `docs/superpowers/plans/2026-06-18-mobile-app-plan.md`

---

## 核心架构

电脑端新增独立 Flask 移动接入服务（端口 8900-8999）+ Flutter App（Dio + Bearer token + 响应式 UI）。

- **移动接入服务** (`MobileAccessServer`) 运行在独立端口，与主 Flask API（端口 5000）隔离
- **令牌配对流程：** PC 生成 6 位配对码 + QR → 手机扫码/手动输入 → PC 确认/拒绝 → 手机获取 Bearer token
- **Flutter App：** Dio HTTP 客户端 + Bearer token 自动注入 + SharedPreferences 持久化

---

## 电脑端文件清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/mobile_access_server.py` | 移动接入服务核心：TokenManager（配对/验证/持久化/_device_map/_upload_counts）、MobileAccessServer（所有 /api/mobile/* 端点）、`generate_mobile_qr()` |
| `frontend/src/components/dialogs/MobileDeviceManager.tsx` | 移动设备管理对话框（开关服务、QR 二维码、配对请求、已配对设备列表、撤销） |
| `test/unit/test_mobile_access_server.py` | 11 个单元测试（后扩展至 17 个） |

### 修改文件

| 文件 | 说明 |
|------|------|
| `backend/api_server.py` | 添加 9 个 /api/mobile/* 桥接端点（status/enable/disable/qr/pending-request/confirm-pairing/devices/revoke/revoke-all） |
| `src/BlurArc.py` | 添加 `_start_mobile_service()` 自动启动逻辑，Flask 就绪后根据配置自动启动移动服务 |
| `frontend/src/services/api.ts` | 添加 8 个移动 API 方法 |
| `frontend/src/contexts/I18nContext.tsx` | 添加 8 组中英 i18n 字符串 |
| `frontend/src/components/layout/Header.tsx` | 添加 📱 按钮入口，打开 MobileDeviceManager |

---

## Flutter App 文件清单（16 → 22 个 Dart 文件）

| 文件 | 说明 |
|------|------|
| `blurarc_app/pubspec.yaml` | 项目配置 + 依赖（dio, cached_network_image, video_player, mobile_scanner, shared_preferences 等） |
| `blurarc_app/lib/main.dart` | 入口 + Material Dark 主题 + 路由 |
| `blurarc_app/lib/services/api_client.dart` | Dio HTTP 客户端 + Bearer token 注入 + `pairAndPoll()` 配对轮询 + `setConnectionParams()` |
| `blurarc_app/lib/screens/connect_screen.dart` | 扫码/手动输入连接 + 配对码输入（后改为 mDNS 发现流程） |
| `blurarc_app/lib/screens/album_screen.dart` | 相册首页（手机全屏/平板分栏自适应） |
| `blurarc_app/lib/screens/photo_grid_screen.dart` | 照片网格 + 无限滚动分页 |
| `blurarc_app/lib/screens/photo_preview_screen.dart` | 全屏预览 + 视频播放 + EXIF 信息面板 |
| `blurarc_app/lib/screens/upload_screen.dart` | 照片推送 + 进度追踪 |
| `blurarc_app/lib/screens/pairing_code_screen.dart` | 6 位配对码输入页（配对重设计新增） |
| `blurarc_app/lib/screens/home_page.dart` | 三 Tab 首页（相册/上传/设置）（配对重设计新增） |
| `blurarc_app/lib/screens/settings_screen.dart` | 设置页（连接信息 + 重新配对 + 关于）（配对重设计新增） |
| `blurarc_app/lib/models/album_tree.dart` | TreeNode 数据模型 |
| `blurarc_app/lib/models/photo.dart` | Photo 数据模型 |
| `blurarc_app/lib/models/upload_item.dart` | UploadStatus enum + UploadItem class（配对重设计新增） |
| `blurarc_app/lib/widgets/tree_view.dart` | 年份/月份目录树组件 |
| `blurarc_app/lib/widgets/photo_card.dart` | 缩略图卡片组件 |
| `blurarc_app/lib/widgets/responsive_layout.dart` | 自适应布局组件 |
| `blurarc_app/lib/widgets/upload_progress.dart` | 上传进度条组件 |
| `blurarc_app/lib/services/mdns_discovery.dart` | mDNS 设备发现服务（占位实现）（配对重设计新增） |

---

## 后端 API 端点清单

### 主 Flask（端口 5000）— 桥接端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/mobile/status` | GET | 查询移动服务状态（enabled/running/port/ip/paired_count） |
| `/api/mobile/enable` | POST | 启动移动接入服务 |
| `/api/mobile/disable` | POST | 停止移动接入服务（调用 `revoke_all()` 清空 token） |
| `/api/mobile/qr` | GET | 获取配对 QR 二维码 PNG |
| `/api/mobile/pending-request` | GET | 查询待确认的配对请求 |
| `/api/mobile/confirm-pairing` | POST | 确认/拒绝配对请求 |
| `/api/mobile/devices` | GET | 获取已配对设备列表 |
| `/api/mobile/revoke` | POST | 撤销单个设备令牌 |
| `/api/mobile/revoke-all` | POST | 撤销所有设备令牌 |

### 移动接入服务（端口 8900-8999）— 直接端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/pair` | GET | 生成 6 位配对码 + QR 内容 |
| `/api/mobile/pair-request` | POST | 手机端提交配对请求（code + device_name） |
| `/api/mobile/pair-status` | GET | 查询配对状态（accepted→返回 token, pending, expired, invalid） |
| `/api/mobile/verify` | GET | 验证 Bearer token 有效性 |
| `/api/mobile/stats` | GET | 获取相册统计 |
| `/api/mobile/tree` | GET | 获取目录树 |
| `/api/mobile/photos` | GET | 分页获取照片列表 |
| `/api/mobile/thumbnail` | GET | 获取缩略图 |
| `/api/mobile/file` | GET | 获取原始文件 |
| `/api/mobile/preview` | GET | 获取预览图 |
| `/api/mobile/exif` | GET | 获取 EXIF 数据 |
| `/api/mobile/upload` | POST | 上传照片文件 |

### 配对重设计新增端点（/api/mobile/pairing/*）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/mobile/pairing/request` | POST | 手机请求配对（提交 device_name） |
| `/api/mobile/pairing/pending` | GET | PC 轮询待确认设备 |
| `/api/mobile/pairing/confirm` | POST | PC 确认配对（生成 6 位配对码） |
| `/api/mobile/pairing/reject` | POST | PC 拒绝配对 |
| `/api/mobile/pairing/submit-code` | POST | 手机提交配对码（验证成功返回 token） |
| `/api/mobile/pairing/status` | GET | 查询配对状态 |
| `/api/mobile/pairing-mode/start` | POST | 开启配对模式（启动 mDNS 广播） |
| `/api/mobile/pairing-mode/stop` | POST | 关闭配对模式 |

---

## 配对流程

### 旧流程（兼容保留）

```
PC: 开启服务 → 生成 6 位配对码 + QR 二维码
Phone: 扫码/手动输入 → POST /api/mobile/pair-request (code + device_name)
Phone: 轮询 GET /api/mobile/pair-status?code=XXX → pending/accepted(含token)/expired/invalid
PC: 前端轮询 /api/mobile/pending-request → 显示配对请求 → 确认/拒绝
PC确认: POST /api/mobile/confirm-pairing → 生成 token → phone 轮询获取 token
Phone: 保存 token → Bearer 认证 → 浏览相册/推送照片
```

### 新流程（重设计，2026-06-18 实施）

```
Phone: mDNS 发现 _blurarc._tcp.local. → 获取 PC IP:port
Phone: 连接 PC → 提交配对请求（device_name）
PC: 前端轮询 /api/mobile/pairing/pending → 显示待确认设备
PC: 用户确认 → 生成 6 位配对码（120 秒有效）
Phone: 用户输入配对码 → POST /api/mobile/pairing/submit-code
验证成功 → 返回 Bearer token
Phone: 保存 token → 浏览相册/推送照片
```

---

## 代码审查 Critical 修复记录

| ID | 问题 | 修复方式 |
|----|------|---------|
| C1 | 缩略图/预览端点 Path→bytes 误用（`io.BytesIO(Path)`） | 改为 `send_file(str(path), mimetype='image/jpeg')`，与 `api_server.py` 用法一致 |
| C2 | Flutter 配对轮询协议不匹配（调 `/pair` 生成新码而非查询状态） | 新增 `/api/mobile/pair-status` 端点 + Flutter `pairAndPoll` 重写为轮询此端点 |
| C3 | 上传端点无速率/并发控制 | 添加 `MAX_CONTENT_LENGTH` + content-length 预检 + session 文件计数限制（2000）+ `secrets` 替代 `random` 生成配对码 |

---

## 遗留问题修复记录

| # | 问题 | 修复方式 | 状态 |
|---|------|---------|------|
| 1 | Flutter android/ios 目录缺失 | 运行 `flutter create .` 补全所有平台配置文件（128 个文件） | ✅ 已修复 |
| 2 | CORS 缺失 | 安装并引入 `flask_cors`，配置允许 `/api/mobile/*` 等端点跨域访问 | ✅ 已修复 |
| 3 | `/pair` rate limiting 缺失 | 添加 IP 级 10 次/分钟限制，超限返回 429 | ✅ 已修复 |
| 4 | device_name 重配对覆盖旧 token | `confirm_pair_request` 中同一 device_name 先撤销旧 token 再生成新 token | ✅ 已修复 |
| 5 | `disable` 不清空 token | `mobile_disable` 端点添加 `server.token_manager.revoke_all()` 调用 | ✅ 已修复 |
| 6 | 端到端联调验证缺失 | 使用 Flask test_client 重写联调测试（17 个测试全部 PASS） | ✅ 已修复 |

---

## 手机上传功能（2026-06-18 第二轮）

实施文档：`docs/superpowers/plans/2026-06-18-mobile-app-plan.md`（Phase 7 手机上传）

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/phone_upload_server.py` | 独立 Flask 服务（端口 9800-9900）+ PIN 认证 + magic bytes 校验 |
| `frontend/src/components/dialogs/ImportDialog/PhoneImportPanel.tsx` | 手机上传面板（PC 前端） |
| `test/unit/test_phone_upload_server.py` | 18 个单元测试 |

### 修改文件

| 文件 | 说明 |
|------|------|
| `backend/api_server.py` | 新增 9 个 /api/phone-upload/* 桥接端点 + CORS 收紧到 localhost/PyWebView |
| `frontend/src/services/api.ts` | 新增 `startPhoneUpload` / `stopPhoneUpload` / `getPhoneUploadStatus` / `discardPhoneSession(sessionId)` 等方法 |
| `frontend/src/contexts/I18nContext.tsx` | 新增手机上传相关 i18n 字符串 |
| `frontend/src/components/dialogs/ImportDialog/ImportDialog.tsx` | 集成 PhoneImportPanel 到导入对话框 |

### 安全机制

- 6 位一次性 PIN（QR 内嵌）+ `secrets.choice` 生成
- `MAX_CONTENT_LENGTH = 500MB`（Werkzeug 全局限制）
- Magic bytes 白名单校验（JPEG/PNG/GIF/MP4/WebM/BMP/TIFF）
- `discard` 端点需 `session_id` 参数二次确认
- CORS 收紧为仅允许 `localhost:5000` + PyWebView origin

### 代码审查修复（第二轮）

| ID | 级别 | 问题 | 修复方式 |
|----|------|------|---------|
| C1 | Critical | CORS 全开放 + discard 无鉴权 | CORS 收紧 + discard 必须传 session_id |
| C2 | Critical | 上传服务器无认证 | 添加 6 位一次性 PIN（QR 内嵌），上传/状态端点需 PIN |
| C3 | Critical | 无 MAX_CONTENT_LENGTH | Flask app 设置 500MB 全局限制 |
| I1 | Important | 文件不校验内容 | magic bytes 白名单校验（拒绝伪装扩展名） |
| I2 | Important | session 清理不健壮 | 添加异常捕获 + 日志 |
| I3 | Important | 前端无错误边界 | 轮询 5 次失败自动切换 error 状态 |
| I4 | Important | discard 无二次确认 | session_id 参数验证（同 C1） |
| I5 | Important | XSS 风险检查 | 确认不存在（模板无动态路径注入） |

---

## 配对重设计实施（2026-06-18 第三轮）

实施计划：`docs/superpowers/plans/2026-06-18-mobile-pairing-redesign-plan.md`

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/zeroconf_publisher.py` | mDNS 广播 `ZeroconfPublisher`（zeroconf ServiceInfo `_blurarc._tcp.local.`） |
| `backend/phone_upload_server.py` | 已存在，本次新增 `PairingManager` 类到 `mobile_access_server.py` |
| `blurarc_app/lib/services/mdns_discovery.dart` | mDNS 设备发现服务（暂为占位实现） |
| `blurarc_app/lib/screens/pairing_code_screen.dart` | 6 位配对码输入页 |
| `blurarc_app/lib/screens/home_page.dart` | 三 Tab 首页（相册/上传/设置） |
| `blurarc_app/lib/screens/settings_screen.dart` | 设置页 |
| `blurarc_app/lib/models/upload_item.dart` | `UploadStatus` enum + `UploadItem` class |

### 修改文件

| 文件 | 说明 |
|------|------|
| `backend/mobile_access_server.py` | 新增 `PairingManager` 类 + 集成 `ZeroconfPublisher` + 12 个新端点 |
| `backend/api_server.py` | 新增 8 个 /api/mobile/pairing/* 桥接端点 |
| `frontend/src/services/api.ts` | 新增 8 个配对 API 方法 |
| `frontend/src/contexts/I18nContext.tsx` | 新增 zh/en 配对 i18n 字符串（16 条） |
| `frontend/src/components/dialogs/MobileDeviceManager.tsx` | 新增配对模式 UI（开启按钮 + 三状态弹窗） |
| `blurarc_app/lib/services/api_client.dart` | 新增 `pairingRequest()` + `submitPairingCode()` + 公共 `host`/`port` getter |
| `blurarc_app/lib/screens/connect_screen.dart` | 重写为 mDNS 自动发现流程 |

---

## 验证状态

- ✅ TypeScript 编译通过（`npx tsc --noEmit`）
- ✅ Python 后端语法检查全部 OK
- ✅ 228 个全量测试通过（6 个已有 `import_manager` 失败与本次修改无关）
- ✅ Flutter `analyze`：**0 issues** ✅
- ✅ `zeroconf>=0.132.0` 已安装，`requirements.txt` 已更新

---

## 数据流（移动接入）

```
手机 App ──HTTP (Bearer token)──→ 移动接入服务 (8900-8999) ──→ 主 Flask API 函数 (5000)
                                         │
PC 前端 ──HTTP──→ 主 Flask (5000) ──→ 桥接端点 ──→ 控制移动服务启停/配对/设备管理
```

---

## 待办

- 真机/模拟器端到端联调（需要 Android SDK 或 iOS 环境）
- 移动端 UI/UX 优化
- `test_zeroconf_publisher.py` 单元测试（Phase 8）
- `test_pairing_manager.py` 单元测试（Phase 8）
- 配对流程集成测试（Phase 8）

---

## 2026-06-18 夜间 第二轮代码审查 + 修复

审查覆盖：`zeroconf_publisher.py`、`PairingManager`、配对桥接端点、`MobileDeviceManager.tsx`、Flutter 配对界面、i18n、API 方法。

### 🔴 C2 (已修复): PairingManager 线程安全
- 主 Flask (`threaded=True`) 和移动接入服务 (`threaded=False` 但不同线程) 同时访问 `PairingManager`
- 修复：添加 `threading.Lock()`，拆分 `_generate_code_unlocked()` 内部方法避免死锁
- 9 个公共方法全部加锁保护

### 🔴 C1 (降级为 Minor): `generate_pairing_code()` 返回 `(code, code)`
- `pair_qr()` 旧端点返回的 `qr` 字段是代码本身，不是 QR 图片
- 确认新配对流程不使用此端点，保留向后兼容即可

### 🟠 I1 (已修复): device_name 输入验证
- `pairing_request()` 新增：空字符串拒绝、50 字符限制、非法字符过滤

### 🟠 I3 (已修复): mobile_photos 空路径
- 开头新增空路径检查，直接返回空结果

### 测试结果
- 35 个移动相关测试全部 PASS，无回归

---

## 📦 发布 v0.5.2 — 2026-06-18

### 版本变更
- 版本号：v0.5.1 → v0.5.2
- 更新 README.md：版本徽章、核心能力（手机互联）、技术栈（Flutter + Zeroconf）、项目结构
- 更新 CHANGELOG.md：新增 [0.5.2] 完整变更记录
- 更新 SPEC.md：版本号、技术架构图、API 接口列表（4.10-4.12）

### Git 提交
- Commit message: `Release v0.5.2: 移动接入功能（Flutter App + 安全配对 + mDNS 发现）`
- Tag: `v0.5.2`

### 新增文件清单
- `backend/zeroconf_publisher.py` — mDNS 广播
- `backend/mobile_access_server.py` — 移动接入服务（12 个端点）
- `frontend/src/components/dialogs/MobileDeviceManager.tsx` — 移动设备管理对话框
- `blurarc_app/lib/screens/pairing_code_screen.dart` — 配对码输入界面
- `blurarc_app/lib/screens/connect_screen.dart` — 连接界面（mDNS 发现）
- `blurarc_app/lib/screens/home_page.dart` — 主页（3 Tab）
- `blurarc_app/lib/services/mdns_discovery.dart` — mDNS 发现服务（stub）
- `test/unit/test_mobile_access_server.py` — 17 个单元测试
- `test/unit/test_phone_upload_server.py` — 18 个单元测试
