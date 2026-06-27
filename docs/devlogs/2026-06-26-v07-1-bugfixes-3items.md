# 2026-06-26 v0.7.1 Bug 修复：心形样式 / 文件夹视图 / 创建相册重复弹窗

## 背景

v0.7 集成后用户测试发现 3 个 UI Bug，涉及 PhotoCard 心形、DirectoryTree 文件夹结构、Sidebar 创建相册流程。

## Bug 一览

| # | Bug | 根因 | 修复 |
|---|-----|------|------|
| 1 | 收藏照片右上角心形与原型不符（已收藏时背景色失效） | `index.css` 未定义 `--color-favorite` 变量，Tailwind v4 `@theme` 中无该 class；PhotoCard 缺小红点指示器 | `@theme` + `.dark` 各加 `--color-favorite` / `--color-favorite-hover`；PhotoCard class 改用 `bg-favorite` + `hover:bg-favorite-hover`；新增 `photo-fav-dot` 小红点 span |
| 2 | 文件夹视图按 YYYY 年份单独分组展示，字体不匹配原型 | `DirectoryTree.tsx` 沿用 v0.6 按 `years` 字段分组渲染，未递归 rootDir 树 | 重写为按 `rootDir.children` 纯递归展开；统一字号 13px / 圆角 6px / hover 浅色背景；保留右键菜单 + 资源管理器入口 |
| 3 | 点 "+ 新建相册" 创建成功后，还会再弹一个"新建相册" modal | `Sidebar.tsx` 自带创建 modal，提交后调用 `onCreateAlbum?.()` → `App.tsx` 又弹 `AlbumManageModal(mode:'create')` | 删 Sidebar 自带的 modal（state、openCreateModal、closeCreateModal、handleCreateAlbum、showCreateModal 块）；按钮 onClick 改为 `handleCreateAlbumClick` 仅触发 `onCreateAlbum?.()`，统一走 App.tsx 的 AlbumManageModal |

## 修改文件

- [frontend/src/index.css](frontend/src/index.css) - 新增 `--color-favorite` / `--color-favorite-hover`（亮色 + 暗色）
- [frontend/src/components/photos/PhotoCard.tsx](frontend/src/components/photos/PhotoCard.tsx) - 心形 button class 重构 + 新增小红点
- [frontend/src/components/sidebar/DirectoryTree.tsx](frontend/src/components/sidebar/DirectoryTree.tsx) - 完全重写为纯递归
- [frontend/src/components/layout/Sidebar.tsx](frontend/src/components/layout/Sidebar.tsx) - 移除自带创建 modal，调用 `onCreateAlbum`

## 设计依据

| Bug | 原型出处 |
|-----|----------|
| 1 | [album-management-v2-light.html:449-478](../prototypes/desktop/album-management-v2-light.html) `.photo-heart.favorited` + `.has-favorite::after` |
| 1 配色 | 原型 CSS 变量 `--favorite: #f43f5e` (亮色) / `#fb7185` (暗色) |
| 2 | [album-management-v2-light.html](../prototypes/desktop/album-management-v2-light.html) Sidebar "文件夹" section |
| 3 | [2026-06-24-v0.7-album-ui-spec.md](../superpowers/specs/2026-06-24-v0.7-album-ui-spec.md) §11.3 验收清单 - 用 AlbumManageModal |

## 验证

- ✅ `npm run build` 通过 (364.89 kB, 486ms)
- ✅ TypeScript 0 错误
- ⏳ 浏览器端到端验证待 MCP 测试
- ⏳ 单元测试待跑

## 后续 TODO

- DirectoryTree 接收的 `years` prop 已废弃（保留兼容），未来可从 Sidebar props 移除
- 暗色模式下小红点的 z-index 与心形 button 协调需 MCP 验证
- Sidebar 的 `description` 字段随 v0.7 spec 移除（AlbumManageModal 不支持 desc），可清理
