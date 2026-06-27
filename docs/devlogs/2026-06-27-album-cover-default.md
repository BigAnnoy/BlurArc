# 相册默认封面拍立得堆叠设计 + 公共组件化

**日期：** 2026-06-27
**分支：** drafts
**提交：** 766e638 → cd4b6a6

## 背景

相册默认封面原先分散在 5 个文件中，用 emoji `📷` + CSS 样式实现，存在以下问题：
- 维护成本高：改一次要动 5 处
- 视觉粗糙：emoji 在不同系统渲染不一致
- 无统一风格：各处尺寸/配色有细微差异

## 目标

1. 创建共享 `AlbumCoverDefault` 组件，集中维护默认封面
2. 设计拍立得堆叠风格 SVG，替换 emoji
3. 支持多尺寸（tile/cover/thumb），所有尺寸显示完整细节（等比缩小）
4. 适配亮色/暗色主题

## 实施

### 1. AlbumCoverDefault 组件

**文件：** `frontend/src/components/common/AlbumCoverDefault.tsx`

**设计要点：**
- **3 层拍立得堆叠**：后层 -16°（opacity 0.32）、中层 +11°（opacity 0.58）、前层 -4°
- **4:3 比例**：外框 100×75，照片区域 84×63
- **装饰元素**：山景线条 + 太阳（圆环 + 8 条射线）+ 淡渐变天空
- **投影**：`feDropShadow` 实现前层卡片投影
- **唯一 ID**：用 `useId()` 生成 SVG filter/gradient ID，避免多实例冲突

**尺寸配置：**
| size | 宽×高 | 用途 |
|------|-------|------|
| tile | 200×200 | 相册集卡片 |
| cover | 100%×100% | 相册详情页大封面 |
| thumb | 36×36 | 侧边栏缩略图 |

所有尺寸使用同一 viewBox（`0 0 200 200`），等比缩放显示完整细节。

### 2. CSS 变量别名映射

**文件：** `frontend/src/index.css`

原型图使用 `--bg-card`、`--stroke-light`、`--stroke`、`--stroke-strong` 变量名，与应用的 `--color-card`、`--color-border` 等不一致。在 `body` 和 `.dark` 中添加别名映射：

```css
body {
  --bg-card: var(--color-card);
  --stroke-light: var(--color-border);
  --stroke: var(--color-text-secondary);
  --stroke-strong: var(--color-text-primary);
}
.dark {
  --bg-card: var(--color-card);
  --stroke-light: var(--color-border);
  --stroke: var(--color-text-secondary);
  --stroke-strong: var(--color-text-primary);
}
```

### 3. 替换 5 处旧实现

| 文件 | 旧实现 | 新实现 |
|------|--------|--------|
| `App.tsx` | `.tile-default` + emoji `📷` | `<AlbumCoverDefault size="tile" />` |
| `Sidebar.tsx` | `.thumb-default` + emoji `📷` | `<AlbumCoverDefault size="thumb" />` |
| `TimelineView.tsx` | 年份/月份文字占位 | `<AlbumCoverDefault size="tile" />` |
| `PhotoPreview.tsx` | emoji `📷` | `<AlbumCoverDefault size="thumb" />` |
| `JoinAlbumModal.tsx` | emoji `📷` + CSS | `<AlbumCoverDefault size="thumb" />` |

### 4. menuBuilders.ts 公共菜单工厂

**文件：** `frontend/src/components/common/menuBuilders.ts`

抽取右键菜单构建逻辑为工厂函数：
- `buildPhotoMenu()` — 照片右键菜单（预览/收藏/相册/资源管理器/删除）
- `buildAlbumMenu()` — 相册右键菜单（打开/重命名/复制/删除）
- `buildDirectoryMenu()` — 目录右键菜单（资源管理器/扫描新照片）

所有回调改为可选，无回调的菜单项自动隐藏。

## 代码审查修复

代码审查发现 2 个确认问题，已修复：

### 1. JoinAlbumModal 相册列表截断（Important）

**问题：** `slice(0, 5)` 硬编码截断，用户有 6+ 相册时无法选择后面的。

**修复：** 移除 `slice(0, 5)` 和 `maxHeight: 234px`，让容器自然滚动。

### 2. PhotoPreview 右键菜单空函数（Important）

**问题：** `onPreview`/`onJoinAlbum`/`onDelete` 为空函数 `() => {}`，点击无反馈。

**修复：** 
- `buildPhotoMenu` 改为可选回调
- PhotoPreview 只传有实现的回调（`onToggleFavorite`/`onOpenInExplorer`）
- 无回调的菜单项自动隐藏

### 审查误报（未修改）

- **useEffect 依赖数组**（Critical 误报）：effect 专门监听 `mainSort` 变化，内部读取的 `state.currentView` 等是最新值，不需要加入依赖数组。
- **`--stroke` 命名冲突**（Important 低风险）：项目内无冲突，暂不改。

## 验收

- ✅ 相册集视图：3 张卡片显示拍立得堆叠封面
- ✅ 侧边栏：thumb 尺寸显示完整细节（等比缩小）
- ✅ TimelineView：年/月卡片无照片时显示默认封面
- ✅ PhotoPreview：相册列表显示 thumb 封面
- ✅ JoinAlbumModal：相册列表显示 thumb 封面，6+ 相册可滚动选择
- ✅ PhotoPreview 右键菜单：只显示有实现的菜单项
- ✅ 亮色/暗色主题：封面颜色自适应
- ✅ 多实例：SVG ID 不冲突

## 涉及文件

**新增：**
- `frontend/src/components/common/AlbumCoverDefault.tsx`
- `frontend/src/components/common/menuBuilders.ts`
- `docs/prototypes/desktop/album-cover-default-v1.html`
- `docs/prototypes/desktop/album-cover-default-v2.html`
- `docs/prototypes/desktop/album-cover-default-v3.html`
- `docs/superpowers/specs/2026-06-27-ui-fixes-design.md`

**修改：**
- `frontend/src/App.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/timeline/TimelineView.tsx`
- `frontend/src/components/dialogs/PhotoPreview.tsx`
- `frontend/src/components/dialogs/JoinAlbumModal.tsx`
- `frontend/src/index.css`
