# 🛠️ Blur Arc 开发指南 v0.6.0

> 同时覆盖 **后端（Python）**、**PC 前端（React）**、**移动端（Flutter）** 的开发流程与约定。
>
> **版本**：v0.6.0（2026-06-24）

---

## 📋 目录

1. [项目结构](#项目结构)
2. [开发环境搭建](#开发环境搭建)
3. [后端开发（Python）](#后端开发python)
4. [PC 前端开发（React）](#pc-前端开发react)
5. [移动端开发（Flutter）](#移动端开发flutter)
6. [调试技巧](#调试技巧)
7. [测试规范](#测试规范)
8. [发布流程](#发布流程)
9. [工程约定](#工程约定)

---

## 项目结构

```
BlurArc/
├── src/BlurArc.py                # PC 端主入口
├── backend/                      # Python 后端
│   ├── api_server.py             # PC 端 API
│   ├── mobile_access_server.py   # 移动端独立 API
│   ├── zeroconf_publisher.py     # mDNS 广播
│   ├── import_manager.py         # 导入 + 去重
│   ├── thumbnail_manager.py      # 缩略图
│   ├── video_processor.py        # FFmpeg
│   ├── database.py               # ORM
│   ├── config_manager.py         # 配置
│   └── ffmpeg_binaries/          # FFmpeg 8.1.1
├── frontend/                     # PC 前端 (React + TS + Vite + Tailwind)
│   └── src/
│       ├── App.tsx
│       ├── components/
│       │   ├── common/  dialogs/  layout/  photos/  sidebar/
│       ├── services/api.ts
│       ├── hooks/
│       ├── stores/
│       ├── types/
│       └── utils/
├── blurarc_app/                  # 移动端 (Flutter)
│   ├── lib/
│   │   ├── main.dart
│   │   ├── screens/              # 10 个页面
│   │   ├── services/             # API / mDNS / 主题
│   │   ├── models/
│   │   ├── widgets/
│   │   └── theme/
│   ├── assets/
│   ├── android/  ios/  web/  macos/  windows/  linux/
│   └── pubspec.yaml
├── docs/                         # 文档
│   ├── devlogs/                  # 每日开发日志
│   ├── superpowers/
│   │   ├── specs/                # 方案
│   │   └── plans/                # 实施计划
│   ├── prototypes/               # UI 原型（HTML）
│   └── *.md                      # API / DB / 开发文档
├── scripts/                      # 启动 / 构建脚本
├── test/                         # 后端 pytest
└── BlurArc.spec                  # PyInstaller
```

---

## 开发环境搭建

### 后端

```bash
# Python 3.10+
python --version

# 虚拟环境（推荐）
python -m venv .venv
.\.venv\Scripts\activate    # Windows
source .venv/bin/activate   # macOS/Linux

# 依赖
pip install -r requirements.txt

# FFmpeg（可选，视频功能需要）
python scripts/download_ffmpeg.py
```

### PC 前端

```bash
# Node.js 18+
node --version

cd frontend
npm install
npm run dev    # 开发模式
# 或
npm run build  # 构建到 dist/
```

### 移动端

```bash
# Flutter SDK 3.44+
flutter --version

cd blurarc_app
flutter pub get
flutter doctor    # 检查环境
```

**dev-start 快捷菜单**：

```bash
.\scripts\dev-start.ps1
# [5] PC 端（前端 build + 启动 BlurArc.py）
# [9] 启动 Flutter
# [10] 启动 Flutter + hot reload
```

---

## 后端开发（Python）

### 启动

```bash
python src/BlurArc.py
```

### 添加新 API 端点

**步骤**：

1. 打开 `backend/api_server.py`
2. 在 `_register_routes()`（或类似函数）注册：
   ```python
   @self.app.route("/api/my-feature", methods=["GET"])
   def my_feature():
       return jsonify({"ok": True})
   ```
3. 写业务逻辑到 `backend/xxx_manager.py`
4. 写测试到 `test/api/test_my_feature.py`

**约定**：

- 所有 API 返回 JSON
- 错误用 `{"ok": False, "error": "..."}` 格式
- 日志用 `logger = logging.getLogger(__name__)`

### 添加新数据库表

1. 打开 `backend/database.py`
2. 加模型类：
   ```python
   class MyTable(Base):
       __tablename__ = "my_table"
       id = Column(Integer, primary_key=True)
       ...
   ```
3. `init_db()` 会自动建表
4. 写 CRUD 函数到独立文件或 `database.py`

### 关键文件

| 文件 | 职责 |
|------|------|
| `api_server.py` | PC 端 REST 端点 |
| `mobile_access_server.py` | 移动端 REST 端点 |
| `zeroconf_publisher.py` | mDNS 广播 |
| `import_manager.py` | 导入 + 去重 |
| `thumbnail_manager.py` | 缩略图 |
| `video_processor.py` | FFmpeg |
| `database.py` | ORM |
| `config_manager.py` | 配置 |
| `utils.py` | MD5 / 工具函数 |

---

## PC 前端开发（React）

### 启动

```bash
cd frontend
npm run dev   # Vite dev server（带 HMR）
```

⚠️ **重要**：dev server 是给浏览器开发用的。如果用 PyWebView 嵌入，需用 `npm run build` 把产物输出到 `frontend/dist/`，PyWebView 才会加载。

### 项目结构

```
frontend/src/
├── App.tsx                     # 根组件
├── main.tsx                    # 入口
├── components/
│   ├── common/                 # 通用组件
│   │   ├── Loading.tsx
│   │   ├── ErrorBoundary.tsx
│   │   └── ThemeToggle.tsx
│   ├── dialogs/                # 弹窗
│   │   ├── ImportDialog.tsx
│   │   ├── SettingsDialog.tsx
│   │   └── PairingDialog.tsx
│   ├── layout/                 # 布局
│   │   ├── MainContent.tsx
│   │   ├── TopBar.tsx
│   │   └── Sidebar.tsx
│   ├── photos/                 # 照片组件
│   │   ├── PhotoCard.tsx
│   │   ├── PhotoGrid.tsx
│   │   └── PhotoPreview.tsx
│   └── sidebar/                # 侧边栏
│       ├── FolderTree.tsx
│       └── DeviceList.tsx
├── services/api.ts             # API 调用
├── hooks/                      # React Hooks
│   ├── usePhotos.ts
│   ├── useImport.ts
│   └── ...
├── stores/                     # 状态（Zustand）
│   ├── selectionStore.ts
│   └── themeStore.ts
├── types/                      # TS 类型
└── utils/                      # 工具函数
```

### 关键约定

- React 19 + TypeScript
- Tailwind 4（className 风格）
- 状态管理用 Zustand
- API 调用用 services/api.ts 统一出口
- 修改 UI **必须先在 `docs/prototypes/` 出 HTML 原型**

### 添加新组件

1. 在 `components/<子目录>/` 创建 `MyComponent.tsx`
2. 用 Tailwind className 写样式（避免 inline style）
3. 写 Props interface
4. 在父组件 import 使用

### 调用 API

```typescript
import { api } from '../services/api';

const data = await api.getAlbumStats();
```

`api.ts` 统一封装 fetch + 错误处理。

---

## 移动端开发（Flutter）

### 启动

```bash
cd blurarc_app
flutter run              # 真机
flutter run -d <id>      # 指定设备
```

热更新：模拟器按 `r`（hot reload）/ `R`（hot restart）。

### 项目结构

```
blurarc_app/lib/
├── main.dart                   # 入口 + Provider 链
├── screens/                    # 页面
│   ├── connect_screen.dart
│   ├── pairing_code_screen.dart
│   ├── home_page.dart
│   ├── album_screen.dart
│   ├── folder_screen.dart
│   ├── month_photo_screen.dart
│   ├── photo_grid_screen.dart
│   ├── photo_preview_screen.dart
│   ├── upload_screen.dart
│   └── settings_screen.dart
├── services/                   # 服务
│   ├── api_client.dart
│   ├── mdns_discovery.dart
│   ├── device_info_service.dart
│   └── theme_provider.dart
├── models/                     # 数据模型
│   ├── photo.dart
│   ├── photo_section.dart
│   └── ...
├── widgets/                    # 通用组件
│   ├── blur_arc_logo.dart
│   ├── photo_card.dart
│   └── ...
└── theme/
    ├── app_theme.dart
    └── colors.dart
```

### 关键约定

- Dart 3.0+（`>=3.0.0 <4.0.0`）
- 状态管理：**Provider**（不是 Riverpod / Bloc）
- HTTP：**Dio**（已配 `sendTimeout: 30s`）
- 主题：Material 3，统一 `app_theme.dart`
- 响应式：手机竖屏用 `bottom_tab_bar`，平板横屏用 `tablet_sidebar`
- 修改 UI **必须先在 `docs/prototypes/mobile/` 出 HTML 原型**

### 添加新页面

1. 在 `screens/` 创建 `MyScreen.dart`
2. 用 `StatelessWidget` 或 `Consumer`（需要状态时）
3. 注册到 `home_page.dart` 的 Tab 列表
4. 写测试到 `test/`

### 调用 API

```dart
import 'package:blurarc/services/api_client.dart';

final api = ApiClient();
final sections = await api.getPhotoSections();
```

`api_client.dart` 自动加 Token、自动处理 mDNS 发现的主机。

### 关键陷阱

| 陷阱 | 正确写法 |
|------|----------|
| mDNS 模拟器无效 | 真机测试；模拟器手动输 IP |
| `image_picker` Android 13+ 权限 | `permission_handler` 申请 |
| 设备名 | `DeviceInfoService` 缓存（不要每次 IPC） |
| 视频播放 | `video_player` 配 `chewie` 可加控件 |

---

## 调试技巧

### 后端日志

```bash
# 默认日志在 BlurArc.log
# 实时看：
Get-Content BlurArc.log -Wait   # PowerShell
tail -f BlurArc.log              # bash
```

### mDNS 失败

```python
from backend.zeroconf_publisher import ZeroconfPublisher
p = ZeroconfPublisher()
p.start()
print(p.wait_ready(timeout=3))   # True = 启动成功
print(p._last_error)              # 失败原因
```

**常见原因**：
- 端口 5353 被占用（`netstat -ano | findstr :5353`）
- 防火墙阻止组播
- WiFi 路由器禁用组播

### 移动端连不上 PC

1. **同 WiFi？** （最常见原因）
2. **PC 防火墙 8900 端口放行？**
   ```powershell
   netsh advfirewall firewall add rule name="BlurArc Mobile" dir=in action=allow protocol=TCP localport=8900
   ```
3. **模拟器手动输 IP？** `10.0.2.2:8900`（Android 模拟器内 10.0.2.2 等于宿主机 localhost）

### 导入慢

- 看进度条：算 MD5 是最慢的一步
- 大文件夹可暂停，配置 prescan 缓存后继续
- 第二次导入同一文件夹应秒过

### PC 前端改了不生效

```bash
# PyWebView 加载的是 dist/，必须 build
cd frontend && npm run build
```

### 移动端热更新没反应

- 模拟器：按 `r`（hot reload）/ `R`（hot restart）
- 真机：重装 APK
- 改了 `pubspec.yaml` → 完整重启

### 端口冲突

| 端口 | 占用方 | 解决 |
|------|--------|------|
| 23986 | PC 端 Flask | 改 `src/BlurArc.py` 中 `WEBVIEW_PORT` |
| 8900 | 移动接入 | 改 `backend/mobile_access_server.py` 中 `MOBILE_PORT` |
| 5353 | mDNS | 罕见，避免改 |

---

## 测试规范

### 后端

```bash
pytest                          # 全量
pytest test/unit/ -v            # 单元
pytest test/api/ -v             # API 集成
pytest test/integration/ -v     # 端到端
```

**写测试**：
- 单元测试：`test/unit/test_<module>.py`
- API 测试：`test/api/test_<feature>_api.py`
- 用 `tmp_path` fixture 隔离测试数据

### 移动端

```bash
cd blurarc_app
flutter test
flutter analyze
```

**写测试**：
- Widget 测试：`test/<feature>_test.dart`
- 用 `WidgetTester` 模拟用户操作

---

## 发布流程

**参考 v0.5.3 范式**：

1. **改代码** → 跑测试 → `cd frontend && npm run build`
2. **版本号**：
   - `frontend/package.json` → `"version": "0.5.3"`
   - `src/BlurArc.py` 窗口标题
3. **CHANGELOG.md**：追加 修复/变更/新增 三段
4. **写 spec/plan**：
   - `docs/superpowers/specs/<date>-vX.Y.Z-release-design.md`
   - `docs/superpowers/plans/<date>-vX.Y.Z-release.md`
5. **git 提交推送**：
   ```bash
   git add .
   git commit -m "release: vX.Y.Z — <主题>"
   git push
   ```
6. **打 tag**：
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z — <主题>"
   git push origin vX.Y.Z
   ```
7. **8 条 AC 验收**（见 plan）
8. **GitHub Release**（手动网页或 `gh release create`）

---

## 工程约定

### 命名

| 类型 | 风格 | 例 |
|------|------|-----|
| Python 文件 / 函数 / 变量 | snake_case | `import_manager.py`, `check_file_size` |
| Python 类 | PascalCase | `ImportManager` |
| React 组件文件 | PascalCase | `PhotoCard.tsx` |
| React Hook | camelCase + use | `usePhotos` |
| TS interface | PascalCase | `PhotoItem` |
| TS 变量 | camelCase | `photoList` |
| Dart 文件 | snake_case | `api_client.dart` |
| Dart 类 | PascalCase | `ApiClient` |
| Dart 变量 | camelCase | `photoList` |

### Commit 信息

```
feat: 新功能
fix: 修复
docs: 文档
refactor: 重构
perf: 性能
chore: 杂项
test: 测试
release: 发布
```

例：`fix(import): MD5 cache 命中时跳过 stat()`

### 分支

- 主分支：`main`
- 不开 PR/MR（单人开发，直接推 main）
- 紧急修复：直接在 main 改

### UI 修改必须先出原型

任何 UI 变更 → 先在 `docs/prototypes/` 改 HTML → 用户确认 → 再写代码

### 移动端 vs PC 端

- 移动端 API 走 `backend/mobile_access_server.py`（独立端口 8900）
- PC 端 API 走 `backend/api_server.py`（PyWebView 23986）
- 共享 `database.py` 和 `media` 表

### Spec 驱动开发

- 设计阶段：`docs/superpowers/specs/`
- 实施阶段：`docs/superpowers/plans/`
- 复盘：`docs/devlogs/<date>-<topic>.md`

### mDNS 参数顺序陷阱

后端 `zeroconf>=0.132.0` 中 `ServiceInfo` 的 `addresses` 是 keyword-only 参数：

```python
# ❌ 错
ServiceInfo(SERVICE_TYPE, name, addresses=[...], port=self.port, ...)

# ✅ 对
ServiceInfo(SERVICE_TYPE, name, port=self.port, addresses=[...], ...)
```

错误写法 → `TypeError: multiple values for 'port'` → 线程静默失败。

---

## 📚 进一步阅读

- [CODE_MAP.md](CODE_MAP.md) — 模块地图
- [API_REFERENCE.md](API_REFERENCE.md) — 全部 API
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) — 数据库表
- [DEPENDENCIES.md](DEPENDENCIES.md) — 依赖列表
- [blurarc_app/README.md](../blurarc_app/README.md) — 移动端 README
- [docs/superpowers/specs/](superpowers/specs/) — 方案库
- [docs/devlogs/](devlogs/) — 每日开发日志

---

**版本**: v0.6.0 · **更新日期**: 2026-06-24
