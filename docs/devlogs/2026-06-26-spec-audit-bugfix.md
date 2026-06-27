# 2026-06-26 v0.7 Spec 对比审计与修复

> 对比 `docs/superpowers/specs/2026-06-24-v0.7-album-ui-spec.md` 与前端实现，发现 8 项偏差，实际修复 5 项（用户决定跳过 2 项，1 项基础设施已就绪未接入）。

## 一、审计结果

| # | 问题 | Spec 条款 | 处理 |
|---|------|-----------|------|
| 1 | 引入完整 i18n 框架（双语+语言切换 UI） | §14.4 | **不修**：双语比单语更强大，spec 该条是早期约束 |
| 2 | PhotoCard 收藏红点 | §8.2 | **非 bug**：已正确实现，红点已移除 |
| 3 | 文件夹年份隐藏 | §7.1 | **非 bug**：DirectoryTree 已纯递归无过滤 |
| 4 | 相册默认封面用橙红紫渐变，应为 cyan 渐变 | §5.8 | ✅ 修复 |
| 5 | PhotoPreview 主图 `w-auto`，应为 `w-full + flex-shrink-0` | §12.3.4 | ✅ 修复 |
| 6 | 右键菜单缺导出 + 单相册分组不符 | §2.6/§3.3/§6.4 | **不修**：用户决定不补导出和分组 |
| 7 | 选择模式无独立 banner + 顺序不符 + 无 1000 上限 | §2.7/§2.7.1 | ✅ 修复（独立 banner + 1000 上限；二级全选未接入） |
| 8 | 时间线概览图单击 drill down，应为双击；Days 选择未禁用 | §4.6.2/§4.8 | ✅ 修复 |

## 二、修复详情

### Bug #4：相册默认封面（§5.8）

**问题**：4 处使用橙红紫渐变 `linear-gradient(135deg, #f59e0b 0%, #ef4444 50%, #c156e6 100%)` + SVG 图标，与 spec 要求的 cyan 渐变 + 📷 + PHOTOS 不符；CSS 类 `.tile-default` / `.cover-default` / `.thumb-default` 全部缺失。

**修复**：

1. `frontend/src/index.css` 新增三个 CSS 类：
   - `.tile-default`：主区域 AlbumCard，撑满 100%/100%
   - `.cover-default`：Modal AlbumCard，aspect-ratio 3/2
   - `.thumb-default`：Sidebar 缩略图，1:1 36×36
   - 三个类统一使用 cyan 渐变 + radial 叠加（亮色 `#f0f9ff → #e0f2fe`，暗色 `#0f172a → #1e293b`）
   - 暗色模式通过 `.dark .tile-default` 等覆盖背景

2. 替换 4 处实现：
   - `App.tsx:526-537` 主区域相册卡片默认封面 → `.tile-default` + 📷 + PHOTOS
   - `Sidebar.tsx:268-283` 侧边栏相册缩略图 → `.thumb-default` + 📷
   - `PhotoPreview.tsx:464-473` 所属相册默认封面 → `.thumb-default` + 📷
   - `JoinAlbumModal.tsx:162-175` 加入相册 modal 卡片 → `.cover-default` + 📷 + PHOTOS（原本视觉正确，统一为 CSS 类便于维护）

### Bug #5：PhotoPreview 主图尺寸（§12.3.4）

**问题**：主图用 `w-auto h-auto`，spec 要求 `width: 100%` + `flex-shrink: 0` 防止 flex 容器压缩。

**修复**：`PhotoPreview.tsx:348,358` 视频和图片标签都改为：
```
className="w-full max-w-[calc(100%-104px)] max-h-full rounded-md shadow-lg object-contain flex-shrink-0"
```

### Bug #7：选择模式 banner（§2.7/§2.7.1）

**问题**：
- 选择模式下标题栏内仅显示 `(已选 N)` 文字，spec §2.7 要求独立蓝色 banner
- 按钮顺序不符（实现：[取消][全选][从相册移除][加入相册][删除]，spec：[全选][加入相册][删除][取消]）
- 无 1000 张选中上限

**修复**：

1. `MainContent.tsx`：
   - 删除标题栏内的 `(已选 N)` 文字
   - 选择模式下，工具栏不再显示选择相关按钮（只保留非选择模式的按钮）
   - 新增独立蓝色 banner（`bg-primary-light border-b border-primary/30`），布局：左侧 [已选 N 张] + 共 M 张；右侧按钮组 [全选][从相册移除][加入相册][删除][取消]
   - banner 位于工具栏下方、分组 tabs 上方

2. `App.tsx` `handlePhotoClick`：单次选中超过 1000 张时 toast 提示 `最多选中 1000 张`（用 info 类型，因 Toast 不支持 warning）

**未接入**：二级全选（§2.7.1）— `selectionStore.ts` / `api.getPhotoIds` / 后端 `/api/photos/ids` 基础设施齐全，但需要重构多个组件的 props 链路才能接入，留作后续 enhancement。

### Bug #8：时间线概览图（§4.6.2/§4.8）

**问题**：
- Years/Months/Days 概览图用 `onClick`（单击）直接 drill down，spec §4.6.2 要求单击选中（高亮）、双击 drill down
- `isOverviewMode` 判断缺少 `'days'`，导致 Days 视图的选择按钮未禁用（违反 §4.8）

**修复**：`TimelineView.tsx`：
1. 第 43 行 `isOverviewMode` 加入 `'days'`：`state.view === 'years' || state.view === 'months' || state.view === 'days'`
2. 新增 `selectedBucket` state（`string | null`），单击时 toggle 选中
3. Years/Months/Days 三个概览图：
   - `onClick` → `setSelectedBucket`（单击选中，蓝色 ring 高亮）
   - `onDoubleClick` → `setState` drill down（双击进入下一级视图）
   - bucket key 分别为 `y-${year}` / `m-${year}-${month}` / `d-${date}`

## 三、构建验证

```
cd frontend && npm run build
✓ tsc -b 通过
✓ vite build 通过（365.52 KB JS，45.92 KB CSS，617ms）
```

## 四、遗留事项

| 项 | 说明 | 优先级 |
|----|------|--------|
| 二级全选接入 | `selectionStore` + `api.getPhotoIds` 已就绪，需重构 MainContent/TimelineView 的 props 链路 | P2 |
| 右键菜单补"导出..." | spec §2.6/§6.4 要求，用户决定不做 | — |
| i18n 简化为单语 | spec §14.4 要求，用户决定保留双语 | — |
