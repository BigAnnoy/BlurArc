# UI 原型目录

> **工作流约定：以后任何 UI 修改，必须先在此目录设计原型，确认后再实施代码。**
>
> **更新日期**: 2026-06-24

## 目录结构

```
prototypes/
├── mobile/       # 手机端原型（竖屏）
├── tablet/       # 平板端原型（横屏）
├── desktop/      # 桌面端原型（PC 端 / Web）
├── pc/           # PC 端原型（旧版兼容）
├── img/          # 通用图片资源
├── _compare/     # 原型 vs 实际实现对比截图
└── modify_prototypes.py   # 原型批量修改脚本
```

## 命名规范

```
<platform>/<feature>-v<version>[-<theme>].html

示例：
mobile/album-v3-dark.html
mobile/album-v3-light.html
tablet/album-v3-dark.html
desktop/album-v3-dark.html
```

- **platform**: `mobile` / `tablet` / `desktop` / `pc`
- **feature**: 功能页面名称（如 `album`、`upload`、`settings`、`connect`）
- **version**: 版本号（`v1`、`v2`、`v3`...），每次大改递增
- **theme**: 可选，`dark` / `light`，同时有暗色和亮色时分别建文件

## 工作流程

1. **设计原型** — 在 `prototypes/<platform>/` 下新建 HTML 文件，用纯 HTML/CSS 模拟目标 UI
2. **预览确认** — 浏览器打开原型文件，与用户确认设计细节
3. **生成方案** — 根据确认的原型生成技术实现方案文档（放 `docs/superpowers/specs/`）
4. **实施代码** — 按方案逐步实施，实施完成后原型保留作为视觉参考

## 现有原型清单

### 📱 Mobile（手机端）

| 文件 | 说明 | 状态 |
|------|------|------|
| `mobile/mobile-app-v3-dark.html` | v3 主框架 — 暗色 | ✅ v0.5.2 实施完成 |
| `mobile/mobile-app-v3-light.html` | v3 主框架 — 亮色 | ✅ v0.5.2 实施完成 |
| `mobile/mobile-app-v3-light.png` | v3 亮色截图（存档） | 🖼️ 视觉存档 |
| `mobile/mobile-app-connect-dark.html` | 连接页（mDNS + 手动）— 暗色 | ✅ v0.5.2 |
| `mobile/mobile-app-connect-light.html` | 连接页 — 亮色 | ✅ v0.5.2 |
| `mobile/icon_data.txt` | 应用图标元数据 | 🛠️ 工具 |

### 📲 Tablet（平板端）

| 文件 | 说明 | 状态 |
|------|------|------|
| `tablet/tablet-app-v3-dark.html` | v3 主框架 — 暗色 | ✅ v0.5.2 实施完成 |
| `tablet/tablet-app-v3-light.html` | v3 主框架 — 亮色 | ✅ v0.5.2 实施完成 |
| `tablet/tablet-app-v3-light.png` | v3 亮色截图（存档） | 🖼️ 视觉存档 |
| `tablet/tablet-app-connect-dark.html` | 连接页 — 暗色 | ✅ v0.5.2 |
| `tablet/tablet-app-connect-light.html` | 连接页 — 亮色 | ✅ v0.5.2 |

### 🖥️ PC（桌面端）

| 文件 | 说明 | 状态 |
|------|------|------|
| `pc/pc-app-v1.html` | PC 端 v1 原型（React 化前） | 📜 旧版存档 |
| `pc/pc-app-v1-preview.png` | v1 预览 | 📜 旧版存档 |
| `desktop/` | React 19 + Tailwind 4 改造后，原型不再维护（直接看代码） | 🔁 代码即设计 |

### 🖼️ 资源 & 对比

| 文件 | 说明 |
|------|------|
| `img/logo.svg` | Logo SVG 源文件 |
| `pc-logo.svg` | 旧 PC Logo |
| `_compare/flutter-tablet-edge-1.png` | Flutter 平板实现 vs 原型对比 |
| `_compare/flutter-tablet-light-1.png` | 同上 |
| `_compare/flutter-tablet-light-2.png` | 同上 |
| `_compare/flutter-tablet-light-3.png` | 同上 |
| `_compare/prototype-tablet-light.png` | 平板原型截图 |

### 🛠️ 工具

| 文件 | 说明 |
|------|------|
| `modify_prototypes.py` | 原型批量改色 / 改 Logo 脚本（v0.5.3 统一 Logo 用） |

## 与代码对应关系

| 原型 | 实施位置 |
|------|----------|
| `mobile/mobile-app-v3-*.html` | `blurarc_app/lib/screens/` (10 个 Dart 页面) |
| `tablet/tablet-app-v3-*.html` | 同上（响应式布局） |
| `mobile/mobile-app-connect-*.html` | `blurarc_app/lib/screens/connect_screen.dart` |
| `tablet/tablet-app-connect-*.html` | 同上 |
| `pc/pc-app-v1.html` | `frontend/src/components/` (React 19) |

## 重要约束

- ⚠️ **任何 UI 变更必须先改这里**，再改代码
- ⚠️ 实施完成后原型保留，便于后续视觉回归
- ⚠️ 原型改动后建议跑 `modify_prototypes.py` 同步 Logo / 配色

---

**最后更新**: 2026-06-24 (v0.6.0 文档同步)
