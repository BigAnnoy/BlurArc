# 2026-06-19 原型 Logo 统一管理 + 手机 App 实施计划

## 背景

HTML 原型文件中的 Logo 存在亮色/暗色主题显示不一致问题。经过多次修复（PNG base64 → SVG），最终确定使用 SVG（和 PC 版 `Logo.tsx` 一致），并统一管理到 `docs/prototypes/img/logo.svg`。

## 完成事项

1. **Logo 统一化**
   - 创建 `docs/prototypes/img/logo.svg`（来自 PC 版 `frontend/src/components/common/Logo.tsx` 的 SVG 设计）
   - 所有 8 个原型 HTML 文件改为引用 `<img src="../img/logo.svg" />`
   - 删除测试文件 `logo_test.svg.html`

2. **手机 App 实施计划**
   - 创建 `docs/plans/2026-06-19-mobile-app.md`
   - 分析原型与现有 Flutter 代码差距
   - 计划 7 个 Task：共享 AppBar、移除子页 Scaffold、匹配连接页 2 步流程

## 涉及的 HTML 原型文件

| 文件 | 类型 | 主题 |
|------|------|------|
| `mobile/mobile-app-v3-dark.html` | 主界面 | 暗色 |
| `mobile/mobile-app-v3-light.html` | 主界面 | 亮色 |
| `mobile/mobile-app-connect-dark.html` | 连接页 | 暗色 |
| `mobile/mobile-app-connect-light.html` | 连接页 | 亮色 |
| `tablet/tablet-app-v3-dark.html` | 主界面 | 暗色 |
| `tablet/tablet-app-v3-light.html` | 主界面 | 亮色 |
| `tablet/tablet-app-connect-dark.html` | 连接页 | 暗色 |
| `tablet/tablet-app-connect-light.html` | 连接页 | 亮色 |

## Logo 管理规范

- 统一文件：`docs/prototypes/img/logo.svg`
- 引用方式：`<img src="../img/logo.svg" alt="Blur Arc Logo" style="width:28px;height:28px;" />`
- 修改 Logo：只改 `img/logo.svg` 即可全局生效
