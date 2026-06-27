# 2026-06-27 UI 修复方案设计

## 背景

Timeline 重构验收通过后，用户反馈 6 个 UI/交互问题。本方案基于代码调研 + 原型图对比，给出每个问题的修复设计。

## 问题清单与修复方案

### 问题 1：toolbar 布局切换改为网格/瀑布流

**现状**：原型图 v2（`docs/prototypes/desktop/album-management-v2-light.html` L1316-1319, L2596-2616）是"网格/瀑布流"切换（切换 `.photo-grid` 的 `layout-masonry` class，column-width 200px 瀑布流）。实现（`PhotoToolbar.tsx` L16-17, L59-73）改成了"正方形/原始比例"切换（切换 `<img>` 的 `object-cover/contain`），行为完全不同。

**用户决策**：改实现为网格/瀑布流切换，匹配原型图。

**修复方案**：

1. **PhotoToolbar.tsx**：
   - `displayMode: 'square' | 'original'` → `layoutMode: 'grid' | 'masonry'`
   - tooltip 文案改为 `t('main.layoutSwitch') + '（网格）'` / `'（瀑布流）'`
   - 高亮态条件改为 `layoutMode === 'masonry'`
   - SVG 图标保持不变（原型与实现已一致）

2. **PhotoGrid.tsx**：
   - 接收 `layoutMode` prop（替代 `displayMode`）
   - grid 容器 className：`layoutMode === 'masonry'` 时加 `layout-masonry` class
   - 网格模式：保持现有 `grid grid-cols-N gap-1` 布局
   - 瀑布流模式：用 CSS `column-count` / `column-gap` + 卡片 `break-inside: avoid`（参考原型 L305-319）

3. **PhotoCard.tsx**：
   - 去掉 `displayMode === 'square' ? 'object-cover' : 'object-contain'` 逻辑
   - 网格模式：`aspect-square object-cover`（正方形裁切）
   - 瀑布流模式：`w-full h-auto object-cover`（按原始比例高度，column 内自适应）
   - 瀑布流卡片不再固定 `aspect-square`，高度由图片原始比例决定

4. **CSS（index.css）**：新增 `.layout-masonry` 样式
   ```css
   .layout-masonry {
     column-width: 200px;
     column-gap: 6px;
   }
   .layout-masonry > * {
     break-inside: avoid;
     margin-bottom: 6px;
   }
   ```

5. **App.tsx / TimelineView.tsx / MainContent.tsx**：`displayMode` state 改名为 `layoutMode`，默认值 `'grid'`

6. **原型图**：v2 原型已正确，无需改动。spec（`2026-06-24-v0.7-album-ui-spec.md` §3.2.2）更新描述为"网格/瀑布流"。

**影响范围**：所有使用 PhotoToolbar + PhotoGrid 的视图（时间线 All Photos、文件夹、相册、收藏）。

---

### 问题 2：加入相册弹窗对齐 modal v3

**现状**：
- `Modal.tsx` L49 外层 `overflow-y-auto` 导致整个 modal 滚动，header/footer 随滚动消失
- `JoinAlbumModal` 未传 `size`，被 `max-w-md`(448px) 截断，560px 设计宽度失效
- 双重 padding（Modal `p-4` + JoinAlbumModal `px-5`）
- 相册卡片纵向布局（cover 上 + info 下），v3 原型是横向（cover 左 + info 右，48x48 小封面）
- 新建相册入口在网格外，v3 原型在网格内最后一格

**修复方案**：

1. **Modal.tsx 通用组件重构**（对齐 v3 原型 L65-74）：
   - 外层容器：`overflow-y-auto` → `overflow-hidden` + `display: flex; flex-direction: column`
   - 新增 `size='lg'` 选项：`max-w-lg`(512px)，用于 JoinAlbumModal
   - 去掉 children 外层 `<div className="p-4">`，由各 modal 自带 padding
   - header padding：`px-4 py-4` → `px-5 py-4`（20px 横向）
   - close 按钮：方形 `rounded` → 圆形 `rounded-full`，icon `✕` → `×`
   - title 字号：`text-lg` → `text-base`（16px）

2. **JoinAlbumModal.tsx 重写**（对齐 v3 原型 L490-569）：
   - 调用 Modal 时传 `size="lg"`
   - 去掉内层 `<div className="w-[560px]">`（由 Modal size 控制）
   - 搜索区：`px-5 pt-4 pb-3`（保留，与原型 `14px 20px 8px` 接近）
   - 相册网格区：**最多展示 6 个格子（5 个相册 + 1 个新建相册，2 列 × 3 行）**，相册多于 5 个时网格区出现滚动条。`max-h` 按实际 3 行卡片高度计算（约 234px = 68px×3 + 10px×2 gap），`overflow-y-auto p-3`
   - 相册卡片改为横向布局：`flex items-center gap-2.5 p-2.5 border`（cover 48x48 左 + info 右）
   - 封面尺寸：固定 `w-12 h-12`（48x48），不再撑满
   - 选中勾：`w-4.5 h-4.5 rounded-full`（18x18 圆形），位置 `top-1.5 right-1.5`
   - 新建相册入口移入网格内：作为最后一个卡片，`border-dashed`，与普通卡片同构（横向）
   - 去掉多余 `border-t` 分隔线（原型用 padding 自然分隔）
   - footer 文案简化：去掉 title 中的张数（footer 已有）

3. **其他使用 Modal 的组件**：检查并适配新 padding 结构（去掉自带的外层 padding 重复）

**影响范围**：所有使用 Modal 的弹窗（JoinAlbumModal、AlbumManageModal、DeleteConfirmDialog、新建相册等）。

---

### 问题 3：照片预览加完整动效

**现状**：`PhotoPreview.tsx` L183 `if (!photo || !isOpen) return null;` 硬切换，无入场/退出动画。CSS 已有 `animate-fadeIn`/`slideUp`/`modal-in` 类但未使用。信息面板硬切（grid-template-columns 不可过渡）。

**用户决策**：完整动效。

**修复方案**：

1. **PhotoPreview.tsx 入场/退出动画**：
   - 改造为延迟卸载模式：用 `isVisible` state 控制动画，`isOpen=false` 时先播放退出动画再 `setTimeout` 真正卸载
   - 根容器加 `animate-fadeIn`（背景淡入）
   - 主图加 `animate-modal-in`（淡入 + 轻微缩放）
   - 退出时加反向动画类（opacity → 0）

2. **信息面板开合过渡**：
   - 当前 `gridTemplateColumns: '1fr 340px' / '1fr 0'` 硬切 → 改为 `transition: grid-template-columns 0.3s ease`
   - 或改用 `transform: translateX` + `width` 过渡（grid-template-columns 浏览器支持参差，用 transform 更稳）
   - 信息面板内容用 `opacity` 过渡（开合时淡入/淡出）

3. **切换上一张/下一张时主图过渡**：
   - 主图 `<img>` 加 `key={photo.id}` 触发 React 重新挂载
   - 配合 `animate-fadeIn` 实现切换淡入

4. **缩略图条过渡**（如有）：横向滚动平滑

**不引入动画库**（framer-motion 等），用现有 CSS 动画类 + transition。

**影响范围**：PhotoPreview.tsx 及其 CSS。

---

### 问题 4：计数刷新统一为 refreshAllCounters 函数

**现状**：计数刷新分散在 4 处，`refreshAppData`（漏 favorites/albums）、`handleFavoriteChange`（仅 favorites）、`albums:changed` 事件（仅 albums）、TimelineView useEffect。加入相册/拖拽加入相册/复制相册/删除/扫描新增都漏刷。

**用户决策**：统一 `refreshAllCounters` 函数。

**修复方案**：

1. **App.tsx 新增 `refreshAllCounters` 函数**：
   ```tsx
   const refreshAllCounters = useCallback(async () => {
     const [stats, tree, favorites, albums] = await Promise.all([
       api.getStats(),
       api.getTree(),
       api.getFavorites(),
       api.getAlbums(),
     ]);
     setStats(stats);
     setRootDir(tree);
     setFavoriteCount(favorites.length);
     window.dispatchEvent(new Event('albums:changed'));
   }, []);
   ```

2. **Sidebar.tsx 监听 `albums:changed`**：已有（L66），保持不变。`refreshAllCounters` 派发事件后 Sidebar 自动刷新 albums。

3. **各操作后调用 `refreshAllCounters`**：
   - `JoinAlbumModal.onJoined`：加 `await refreshAllCounters()`
   - `Sidebar.addPhotoToAlbum`（拖拽加入）：加 `await refreshAllCounters()`
   - `handleDeleteComplete`：替换 `loadPhotos` 为 `refreshAllCounters` + `loadPhotos`
   - `handleAlbumAction` duplicate：加 `refreshAllCounters()`
   - `DirectoryTree.handleScanNewFiles`：加 `refreshAllCounters()`
   - `handleFavoriteChange`：可改为 `refreshAllCounters()`（覆盖 favorites + 其他可能受影响的）
   - `refreshAppData`：改为调用 `refreshAllCounters` + `loadPhotos`

4. **性能优化**：`Promise.all` 并行拉取 4 个 API，避免串行延迟。API 响应应快（已是索引查询）。

**影响范围**：App.tsx、Sidebar.tsx、JoinAlbumModal.tsx、DirectoryTree.tsx、PhotoPreview.tsx（onPhotoUpdate）。

---

### 问题 5：右键菜单通用化

**现状**：`ContextMenu` 组件通用（纯展示），但使用层面不统一：
- 4 个调用点各自手写 `groups` 数组
- i18n 不一致（Sidebar 用 `t()`，PhotoCard/DirectoryTree 硬编码中文）
- 相册卡片右键直接重命名（不弹菜单），与侧边栏不一致
- PhotoPreview 无右键菜单
- 无动画

**修复方案**：

1. **新增菜单工厂函数**（`frontend/src/components/common/menuBuilders.ts`）：
   ```tsx
   export function buildPhotoMenu(opts: {
     isFavorite: boolean;
     inAlbumId?: string;
     onPreview: () => void;
     onToggleFavorite: () => void;
     onJoinAlbum: () => void;
     onRemoveFromAlbum?: () => void;
     onOpenInExplorer: () => void;
     onDelete: () => void;
   }): MenuGroup[]

   export function buildAlbumMenu(opts: {
     onOpen: () => void;
     onRename: () => void;
     onDuplicate: () => void;
     onDelete: () => void;
   }): MenuGroup[]

   export function buildDirectoryMenu(opts: {
     onOpenInExplorer: () => void;
     onScanNew: () => void;
   }): MenuGroup[]
   ```

2. **统一文案函数**：所有菜单项文案用 `t()` 函数（项目已有 I18nContext），新增 key（`menu.preview`、`menu.toggleFavorite`、`menu.joinAlbum`、`menu.removeFromAlbum`、`menu.openInExplorer`、`menu.delete`、`menu.open`、`menu.rename`、`menu.duplicate`、`menu.scanNew`）。

3. **各调用点改用工厂函数**：
   - `PhotoCard.tsx`：`buildPhotoMenu(...)` 替代内联 groups
   - `Sidebar.tsx` 相册列表：`buildAlbumMenu(...)`
   - `DirectoryTree.tsx`：`buildDirectoryMenu(...)`
   - `App.tsx` 相册卡片：改用 `ContextMenu` + `buildAlbumMenu`（与侧边栏一致，弹菜单而非直接重命名）

4. **PhotoPreview 加右键菜单**：用 `buildPhotoMenu`，操作与 PhotoCard 对称。

5. **ContextMenu 加入场动画**：加 `animate-slideUp` 或 `animate-modal-in`（轻微缩放）。

**影响范围**：ContextMenu.tsx、PhotoCard.tsx、Sidebar.tsx、DirectoryTree.tsx、App.tsx、PhotoPreview.tsx、I18nContext.tsx。

---

### 问题 6：排序逻辑统一

**现状**：
- 时间线排序是全局排序（API ORDER BY），前端 `groupPhotosByDay` 仅按日期字符串降序排列"组"，组内保留全局顺序。组间永远降序（L91 写死 `b[0].localeCompare(a[0])`），与 sort 选项不一致。
- MainContent 的 sort 菜单完全不生效（不传后端）。
- sortOptions 含"按导入日期排序"，用户表示对导入日期不敏感，要求删除。

**用户决策**：组间随 sort 变化 + MainContent sort 生效；删除导入日期排序选项。

**修复方案**：

1. **删除导入日期排序选项**：
   - `TimelineView.tsx` sortOptions：去掉 `import_date_desc` / `import_date_asc`，仅保留 `media_date_desc` / `media_date_asc`
   - `MainContent.tsx` sortOptions：同上（保留 `manual` 手动拖拽选项）
   - 后端 `/api/timeline/photos`、`/api/photos/favorites`：保留 import_date 排序逻辑（不删，兼容性），但前端不再传

2. **时间线组间顺序随 sort 变化**：
   - `groupPhotosByDay` 函数：组间排序方向由 sort 参数决定
   ```tsx
   const groupPhotosByDay = (photos: Photo[], sort: string) => {
     // ... 分组逻辑不变
     const groupOrder = sort === 'media_date_asc'
       ? (a, b) => a[0].localeCompare(b[0])   // 升序：旧→新
       : (a, b) => b[0].localeCompare(a[0]);  // 降序：新→旧
     return Object.entries(groups).sort(groupOrder);
   };
   ```
   - 调用处传 sort 参数

3. **MainContent sort 传后端生效**：
   - `api.getPhotos`（文件夹视图）：加 `sort` 参数
   - `api.getAlbumPhotos`（相册视图）：加 `sort` 参数
   - `api.getFavorites`：加 `sort` 参数
   - 后端 `/api/album/photos`：加 `sort` 参数支持（当前固定按文件名字母序）
   - 后端 `/api/albums/<id>/photos`：加 `sort` 参数支持（当前按加入顺序）
   - 后端 `/api/photos/favorites`：已有 sort 支持，前端开始传
   - MainContent `handleSortChange`：`setSort` 后触发重新加载（加入 useEffect 依赖）

4. **MainContent 分组与排序的交互**：
   - `PhotoGrid.groupPhotosByDate`：同样让组间顺序随 sort 变化
   - 组内保留 API 返回顺序（全局排序）

5. **手动拖拽模式**：保留 `sort === 'manual'` 启用拖拽，但拖拽持久化（TODO）不在本次范围。

**影响范围**：TimelineView.tsx、MainContent.tsx、PhotoGrid.tsx、api.ts、api_server.py。

---

### 问题 7：相册封面策略 + 默认封面重新设计

**现状**：
- 后端 Album 模型有 `cover_photo_id` 字段（v0.7 新增），但前端无任何设置入口，所有相册 `cover_photo_id` 为 null。
- 当前所有相册显示默认封面：cyan 渐变背景 + 📷 emoji + "PHOTOS" 文字（`index.css` L291-369，3 个尺寸变体 `tile-default`/`cover-default`/`thumb-default`）。
- 亮色和暗色模式已有区分（`.dark` 覆盖）。

**用户决策**：
- 封面策略：自动选相册中拍摄日期最新的一张照片作为封面，无照片时用默认封面。
- 默认封面重新设计：照片堆叠轮廓风格（SVG 纯线条，无 emoji），分亮色/暗色。

**修复方案**：

1. **后端封面策略**（`api_server.py` `/api/albums` 查询 L2699-2714）：
   - 查询相册时，若 `cover_photo_id` 为 null，自动选该相册中 `media_date` 最新的照片作为封面
   - **性能优化**：使用 eager loading 或批量查询，避免 N+1 问题
   ```python
   # 批量查询所有相册的最新照片
   album_latest_photos = db.query(
       Album.id,
       Photo.path
   ).outerjoin(
       Album.photos
   ).filter(
       Photo.media_date == db.query(func.max(Photo.media_date)).filter(Photo.album_id == Album.id)
   ).all()
   
   # 构建映射
   latest_photo_map = {album_id: photo_path for album_id, photo_path in album_latest_photos}
   
   for album in albums:
       cover_path = None
       if album.cover_photo_id:
           cover_photo = db.query(Photo).filter(Photo.id == album.cover_photo_id).first()
           if cover_photo:
               cover_path = cover_photo.path
       elif album.id in latest_photo_map:  # 无显式封面，自动选最新照片
           cover_path = latest_photo_map[album.id]
       # ... 其余不变
   ```
   - `/api/albums/<id>/photos` 同样处理
   - 不改数据库，不改 `cover_photo_id`，纯查询时计算

2. **默认封面新设计**（拍立得堆叠风格）：
   - 设计原型：`docs/prototypes/desktop/album-cover-default-v3.html`
   - 视觉描述：3 张拍立得错落堆叠（后层 -16° 左偏、中层 +11° 右偏、前层 -4° 微倾），前层完整显示（淡渐变背景 + 山景线条 + 太阳装饰 + 投影），后两层逐级淡出（opacity 0.32/0.58）。外框和照片区域均为 4:3 比例。
   - **统一维护**：SVG 定义在公共组件 `frontend/src/components/common/AlbumCoverDefault.tsx`，通过 `size` prop 控制尺寸：
     ```tsx
     interface Props { size: 'tile' | 'cover' | 'thumb'; }
     export function AlbumCoverDefault({ size }: Props) {
       // 渲染拍立得堆叠 SVG（3 层错落 + 前层山景太阳装饰）
       // 尺寸：tile=200×200, cover=按容器宽高比, thumb=36×36
     }
     ```
   - 所有使用处引用该组件，未来调整封面设计只需修改 `AlbumCoverDefault.tsx` 一处
   - 亮色模式：背景 `bg-card`（白），线条 `stroke-text-tertiary`（深灰）
   - 暗色模式：背景 `bg-card`（深灰），线条 `stroke-text-tertiary`（浅灰）—— 用 CSS 变量自动适配
   - 去掉 📷 emoji 和 "PHOTOS" 文字

3. **各组件改用公共组件**：
   - `App.tsx` 相册卡片：`<div className="tile-default">📷 PHOTOS</div>` → `<AlbumCoverDefault size="tile" />`
   - `JoinAlbumModal.tsx`：`<div className="cover-default">📷 PHOTOS</div>` → `<AlbumCoverDefault size="thumb" />`（48x48 正方形容器）
   - `Sidebar.tsx` 相册缩略图：`<div className="thumb-default">📷</div>` → `<AlbumCoverDefault size="thumb" />`

4. **CSS 清理**（`index.css` L291-369）：
   - 删除 `.tile-default` / `.cover-default` / `.thumb-default` 的背景渐变、emoji、label 样式
   - 保留容器尺寸约束（width/height/aspect-ratio），背景改为纯 `bg-page`
   - 删除 `.dark` 覆盖的渐变样式（SVG 用 CSS 变量自动适配暗色）

**影响范围**：api_server.py、AlbumCoverDefault.tsx（新建）、App.tsx、JoinAlbumModal.tsx、Sidebar.tsx、index.css。

---

### 问题 8：Timeline 年/月卡片布局对齐相册集

**现状**：`TimelineView.tsx` 年/月卡片用"封面上 + 文字下"纵向布局，固定 220px 高度下文字区仅 44px，计数行被截断。且卡片标题硬编码汉字（`{y.year}年`、`{m.year}年{m.month}月`），英文模式未走 i18n。

**用户决策**：年/月卡片改用相册卡片同构样式——封面填满整个卡片，文字叠加在封面底部（渐变遮罩 + 白字）。

**修复方案**：

1. **TimelineView.tsx 年/月卡片结构**（参考 [App.tsx 相册卡片](file:///f:/AI/Frame_Album/frontend/src/App.tsx#L548-L562)）：
   ```tsx
   <div className="relative rounded-md overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
        style={{ minHeight: '220px' }}
        onDoubleClick={() => setState({ view: 'all', year: y.year })}>
     {/* 封面填满 */}
     {covers.length >= 4 ? (
       <div className="w-full h-full grid grid-cols-2 grid-rows-2 gap-0.5">
         {covers.slice(0, 4).map((p, i) => (
           <img key={i} src={api.getThumbnail(p)} className="w-full h-full object-cover" loading="lazy" />
         ))}
       </div>
     ) : covers.length > 0 ? (
       <img src={api.getThumbnail(covers[0])} className="w-full h-full object-cover" loading="lazy" />
     ) : (
       <AlbumCoverDefault size="tile" />
     )}
     {/* 文字叠加底部（与相册卡片一致）*/}
     <div className="absolute bottom-0 left-0 right-0 px-3 py-2.5 bg-gradient-to-t from-black/65 to-transparent text-white">
       <div className="text-sm font-medium truncate">{t('timeline.yearLabel', { year: y.year })}</div>
       <div className="text-[11px] font-mono opacity-85 mt-0.5">{t('main.photoCount', { count: y.count })}</div>
     </div>
   </div>
   ```

2. **网格布局对齐相册集**：
   ```tsx
   <div className="grid gap-2 p-3"
        style={{
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gridAutoRows: '220px',
          alignContent: 'start',
        }}>
   ```
   （与 [App.tsx 相册集 grid](file:///f:/AI/Frame_Album/frontend/src/App.tsx#L532-L538) 完全一致）

3. **i18n**：年/月标题改用 `t('timeline.yearLabel', { year })` / `t('timeline.yearMonthLabel', { year, month })`，计数改用 `t('main.photoCount', { count })`。

4. **移除旧结构**：删除 `aspect-square` 容器、`p-3` 文字区、`h-[calc(100%-44px)]` 封面区。

**原型图**：[docs/prototypes/desktop/timeline-overview-cards-v1.html](file:///f:/AI/Frame_Album/docs/prototypes/desktop/timeline-overview-cards-v1.html)

---

## 涉及文件总览

| 类别 | 文件 | 涉及问题 |
|------|------|---------|
| 公共组件 | frontend/src/components/common/PhotoToolbar.tsx | 1 |
| 公共组件 | frontend/src/components/common/Modal.tsx | 2 |
| 公共组件 | frontend/src/components/common/ContextMenu.tsx | 5 |
| 公共组件 | frontend/src/components/common/menuBuilders.ts（新建） | 5 |
| 公共组件 | frontend/src/components/common/AlbumCoverDefault.tsx（新建） | 7 |
| 对话框 | frontend/src/components/dialogs/JoinAlbumModal.tsx | 2, 7 |
| 对话框 | frontend/src/components/dialogs/PhotoPreview.tsx | 3, 5 |
| 照片组件 | frontend/src/components/photos/PhotoCard.tsx | 1, 5 |
| 照片组件 | frontend/src/components/photos/PhotoGrid.tsx | 1, 6 |
| 布局 | frontend/src/components/layout/MainContent.tsx | 1, 6 |
| 布局 | frontend/src/components/layout/Sidebar.tsx | 4, 5, 7 |
| 侧边栏 | frontend/src/components/sidebar/DirectoryTree.tsx | 4, 5 |
| 时间线 | frontend/src/components/timeline/TimelineView.tsx | 1, 6, 8 |
| 入口 | frontend/src/App.tsx | 1, 4, 5, 7 |
| 服务 | frontend/src/services/api.ts | 6 |
| i18n | frontend/src/contexts/I18nContext.tsx | 1, 5 |
| 样式 | frontend/src/index.css | 1, 3, 7 |
| 后端 | backend/api_server.py | 6, 7 |
| Spec | docs/superpowers/specs/2026-06-24-v0.7-album-ui-spec.md | 1 |

## 验收标准

### 问题 1
- [ ] toolbar 按钮点击切换"网格/瀑布流"
- [ ] 网格模式：正方形卡片，`aspect-square object-cover`
- [ ] 瀑布流模式：按原始比例高度，`column-width: 200px`
- [ ] tooltip 显示"布局切换（网格）"/"布局切换（瀑布流）"
- [ ] 所有视图（时间线/文件夹/相册/收藏）均可切换

### 问题 2
- [ ] 加入相册弹窗宽度 512px（size=lg）
- [ ] header/footer 固定，仅相册网格区滚动
- [ ] 相册网格区最多展示 6 个格子（5 个相册 + 1 个新建相册），相册多于 5 个时滚动
- [ ] 无双重 padding
- [ ] 相册卡片横向布局（cover 48x48 左 + info 右）
- [ ] 新建相册入口在网格内最后一格（虚线边框）
- [ ] close 按钮圆形，icon ×
- [ ] AlbumManageModal 布局正常
- [ ] DeleteConfirmDialog 布局正常
- [ ] 新建相册弹窗布局正常

### 问题 3
- [ ] 打开预览：背景淡入 + 主图缩放淡入
- [ ] 关闭预览：淡出后卸载（非硬切）
- [ ] 信息面板开合：平滑过渡（非硬切）
- [ ] 切换上一张/下一张：主图淡入过渡
- [ ] 无动画库引入

### 问题 4
- [ ] 加入相册后相册计数立即更新
- [ ] 拖拽加入相册后计数更新
- [ ] 删除照片后所有相关计数更新
- [ ] 扫描新增后文件夹计数更新
- [ ] 复制相册后相册列表更新
- [ ] refreshAllCounters 并行拉取 4 个 API

### 问题 5
- [ ] 所有右键菜单文案用 t() 国际化
- [ ] PhotoCard/Sidebar/DirectoryTree/App 用菜单工厂函数
- [ ] 相册卡片右键弹菜单（与侧边栏一致）
- [ ] PhotoPreview 有右键菜单
- [ ] ContextMenu 有入场动画

### 问题 6
- [ ] sortOptions 无"按导入日期排序"
- [ ] 时间线选"日期升序"时，日期组从旧→新排列
- [ ] 时间线选"日期降序"时，日期组从新→旧排列
- [ ] MainContent 文件夹视图 sort 生效
- [ ] MainContent 相册视图 sort 生效
- [ ] MainContent 收藏视图 sort 生效
- [ ] MainContent 切换 sort 后照片重新加载

### 问题 7
- [ ] 有照片的相册自动显示最新照片作为封面（无需手动设置）
- [ ] 无照片的相册显示默认封面（拍立得堆叠风格）
- [ ] 默认封面无 emoji 和 "PHOTOS" 文字
- [ ] 默认封面亮色模式：白色背景 + 深灰线条
- [ ] 默认封面暗色模式：深色背景 + 浅灰线条
- [ ] 默认封面在 3 个尺寸（tile/cover/thumb）下都正确渲染
- [ ] 切换主题时默认封面颜色自动适配
- [ ] 所有默认封面均引用 AlbumCoverDefault 组件，无重复 SVG 定义

### 问题 8
- [ ] 年/月卡片结构与相册卡片一致：封面填满 + 文字叠加底部（渐变遮罩 + 白字）
- [ ] 年/月卡片网格布局与相册集一致：`minmax(220px, 1fr)` + `gridAutoRows: 220px`
- [ ] 年标题走 i18n：中文"2026年" / 英文"2026"
- [ ] 月标题走 i18n：中文"2026年6月" / 英文"2026/6"
- [ ] 计数走 i18n：中文"N 张" / 英文"N photos"
- [ ] 计数行不被截断（文字叠加层自适应高度）
- [ ] 双击年/月卡片仍能跳转 All Photos 视图（带 filter）
