# Timeline 交互重构 - 技术实施文档

> **关联方案**：[2026-06-27-timeline-apple-photos-redesign.md](../specs/2026-06-27-timeline-apple-photos-redesign.md)
> **前置条件**：第一步（spec + 原型图）已完成并验证通过
> **目标**：将方案 X 落地为代码，5 个子任务可并行执行

## 1. 任务拆解总览

```
第一波（并行）          第二波              第三波
┌─────────────┐
│ A 后端 API  │ ──┐
└─────────────┘   │
                  │   ┌─────────────┐    ┌─────────┐
┌─────────────┐   ├──>│ D Timeline  │───>│ E 构建  │
│ B App.tsx   │ ──┤   │   View 重构 │    │   验证  │
└─────────────┘   │   └─────────────┘    └─────────┘
                  │
┌─────────────┐   │
│ C 筛选排序  │ ──┘ (C 独立，不阻塞 D)
│   UI 重构   │
└─────────────┘
```

## 2. 任务依赖关系

| 任务 | 依赖 | 可并行 |
|------|------|--------|
| A 后端 API | 无 | ✅ 第一波 |
| B App.tsx 回调 | 无 | ✅ 第一波 |
| C 筛选/排序 UI | 无 | ✅ 第一波 |
| D TimelineView 重构 | A（API filter）+ B（回调） | 第二波 |
| E 构建验证 | A+B+C+D 全部 | 第三波 |

## 3. 任务详细指令

---

### 任务 A：后端 API 调整

**目标**：让 `/api/timeline/photos` 支持只传 year（看整年）或 year+month（看整月）；概览图 API 加分批参数。

**文件**：
- `f:\AI\Frame_Album\backend\api_server.py`
- `f:\AI\Frame_Album\backend\database.py`（如需）

**子任务**：

#### A1: `/api/timeline/photos` 支持 year/month filter

当前代码位置：搜索 `@app.route('/api/timeline/photos')` 或 `def get_timeline_photos`。

当前行为：支持 `year` + `month` + `day` 三个参数（都可选）。

需确认/修改：
- ✅ 只传 `year`（不传 month/day）→ 返回整年照片
- ✅ 只传 `year` + `month`（不传 day）→ 返回整月照片
- ✅ 三个都不传 → 返回所有照片

如果当前代码已经是"都可选"模式，则无需改。如果有强制要求，改为全部可选。

**验证**：用 curl 或浏览器测试：
- `/api/timeline/photos?year=2024` → 返回 2024 年所有照片
- `/api/timeline/photos?year=2024&month=8` → 返回 2024-08 所有照片
- `/api/timeline/photos` → 返回所有照片

#### A2: `/api/timeline/years` 加分批参数

当前代码位置：搜索 `@app.route('/api/timeline/years')`。

修改：
- 加 `?limit=30&cursor=<year>` 参数
- `cursor` 表示"从该年份之前开始"（用于倒序分页）
- 响应加 `next_cursor` 和 `has_next` 字段

响应格式：
```json
{
  "years": [{"year": 2024, "count": 1234, "cover_photo_id": "..."}, ...],
  "next_cursor": 2019,
  "has_next": true
}
```

#### A3: `/api/timeline/months` 加分批参数

当前代码位置：搜索 `@app.route('/api/timeline/months')`。

修改：
- 加 `?limit=30&cursor=<year-month>` 参数
- `cursor` 格式 `"YYYY-MM"`，表示"从该月份之前开始"
- 响应加 `next_cursor` 和 `has_next` 字段

响应格式：
```json
{
  "months": [{"year": 2024, "month": 8, "count": 123, "cover_photo_id": "..."}, ...],
  "next_cursor": "2024-02",
  "has_next": true
}
```

**注意**：
- `/api/timeline/days` API 保留（可能其他地方用），但前端不再调用
- 不破坏现有 API 兼容性（limit/cursor 都可选，不传时返回全部）

---

### 任务 B：App.tsx 补传 TimelineView 批量操作回调

**目标**：公用组件化收尾——给 TimelineView 补传 3 个回调，让选择 banner 的按钮生效。

**文件**：
- `f:\AI\Frame_Album\frontend\src\App.tsx`

**当前状态**：
- TimelineView 已声明 `onSelectAll`/`onDeleteSelected`/`onJoinAlbums` props
- App.tsx 未传这 3 个 props（banner 按钮空操作）
- App.tsx 已有 `handleSelectAll`/`handleDelete`/`handleJoinAlbums`（MainContent 在用）

**修改**：

找到 App.tsx 中 `<TimelineView` 的渲染（搜索 `TimelineView`），补传 3 个回调：

```tsx
<TimelineView
  onPhotoClick={handlePhotoClick}
  selectionMode={state.selectionMode}
  selectedIds={state.selectedIds}
  onSelect={handleSelect}
  onSelectAll={handleSelectAll}        // 新增
  onDeleteSelected={handleDelete}      // 新增
  onJoinAlbums={handleJoinAlbums}      // 新增
  onPhotosChange={(photos) => setState(prev => ({ ...prev, photos }))}
  onJoinAlbum={handleJoinAlbum}
  onDelete={handlePhotoDelete}
  onFavoriteChange={handleFavoriteChange}
/>
```

**验证**：
- 确认 `handleSelectAll`/`handleDelete`/`handleJoinAlbums` 在 App.tsx 中存在（MainContent 用的同名 handler）
- 如果 handler 名字不同，找到对应的并复用

**注意**：
- 不修改 TimelineView.tsx（它已经声明了这些 props）
- 不修改 MainContent.tsx（它已经在用这些回调）

---

### 任务 C：筛选/排序 UI 代码对齐原型图

**目标**：把 FilterMenu/SortMenu 从下拉菜单改为 modal 弹窗（Apple Photos 风格），对齐原型图。

**文件**：
- `f:\AI\Frame_Album\frontend\src\components\common\FilterMenu.tsx`
- `f:\AI\Frame_Album\frontend\src\components\common\SortMenu.tsx`

**原型图参考**：`f:\AI\Frame_Album\docs\prototypes\desktop\album-management-v2-light.html`
- CSS：`.filter-item`（行 700-716）
- HTML：`#modal-filter` / `#modal-sort`（行 1650-1668）
- JS：`openFilterMenu` / `openSortMenu`（行 2060-2185）

**子任务**：

#### C1: FilterMenu.tsx 重构

当前：下拉菜单（`absolute right-0 top-full`，附在按钮下方）

改为：modal 弹窗（`modal-mask` 居中卡片）

新 Props 接口（保持兼容）：
```tsx
interface FilterOption {
  key: string;
  label: string;
  icon: string;
}

interface FilterMenuProps {
  isOpen: boolean;
  options: FilterOption[];
  selected: string[];
  onChange: (selected: string[]) => void;
  onClose: () => void;  // 新增：关闭回调
}
```

新实现要点：
- 外层 `modal-mask`（固定全屏遮罩 + 居中卡片）
- 卡片宽 360px，圆角，白底
- 卡片标题：`筛选`（小号大写）
- 选项用 `.filter-item` 样式：全宽按钮，左 icon（20px）+ label，右 ✓（选中时显示）
- 支持分隔线（`{ type: 'sep' }` 选项）——但本期选项不扩展，保持 4 个
- 点击 mask 或关闭按钮 → `onClose()`
- 点击选项 → toggle 选中（多选），不关闭弹窗

**注意**：PhotoToolbar.tsx 里调用 FilterMenu 的地方需要同步改（加 `onClose` prop）。搜索 `FilterMenu` 找到调用处。

#### C2: SortMenu.tsx 重构

当前：下拉菜单

改为：modal 弹窗（与 FilterMenu 样式一致）

新 Props 接口（保持兼容）：
```tsx
interface SortMenuProps {
  isOpen: boolean;
  onClose: () => void;
  options: SortOption[];
  selected: string;
  onChange: (selected: string) => void;
}
```

新实现要点：
- 与 FilterMenu 相同的 modal-mask 结构
- 卡片标题：`排序`
- 选项用 `.filter-item` 样式
- 点击选项 → `onChange(key)` + `onClose()`（单选，选完关闭）

**注意**：PhotoToolbar.tsx 里调用 SortMenu 的地方需要同步改。搜索 `SortMenu` 找到调用处。

#### C3: PhotoToolbar.tsx 同步调整

FilterMenu/SortMenu 改为 modal 后，PhotoToolbar 里的调用需要调整：
- FilterMenu 加 `onClose` prop
- 去掉外层 `relative` div（modal 不需要相对定位）
- `showFilter`/`showSort` state 管理不变

**验证**：
- `npm run build` 无编译错误
- 筛选/排序按钮点击后弹出居中 modal
- 点 mask 或关闭按钮关闭 modal

---

### 任务 D：TimelineView 代码重构

**目标**：按方案 X 重构 TimelineView——去掉 Days tab，双击直接进 All Photos（带 filter），加分批加载。

**文件**：
- `f:\AI\Frame_Album\frontend\src\components\timeline\TimelineView.tsx`
- `f:\AI\Frame_Album\frontend\src\services\api.ts`

**依赖**：任务 A（后端 API）+ 任务 B（App.tsx 回调）

**子任务**：

#### D1: TimelineViewType 去掉 'days'

```tsx
// 改前
type TimelineViewType = 'all' | 'days' | 'months' | 'years';

// 改后
type TimelineViewType = 'all' | 'months' | 'years';
```

同步修改 `TimelineState` 接口（如有 `day` 字段，保留但不再用于 view tabs）。

#### D2: 删除 days 视图相关代码

- 删除 days 视图的渲染分支（`state.view === 'days'` 的 JSX）
- 删除 days API 调用（`api.getTimelineDays`）
- 删除 `days` state
- 删除 view tabs 里的 Days 按钮
- 删除 `isOverviewMode` 里对 `'days'` 的判断

#### D3: Years/Months 双击直接进 All Photos

改前（逐级下钻）：
```tsx
// Years 卡片
onDoubleClick={() => setState({ view: 'months', year: y.year })}
// Months 卡片
onDoubleClick={() => setState({ view: 'days', year: m.year, month: m.month })}
```

改后（直接进 All Photos）：
```tsx
// Years 卡片
onDoubleClick={() => setState({ view: 'all', year: y.year })}
// Months 卡片
onDoubleClick={() => setState({ view: 'all', year: m.year, month: m.month })}
```

#### D4: 去掉 selectedBucket 状态（单击选中高亮）

- 删除 `selectedBucket` state
- 删除卡片 `onClick` 里的 `setSelectedBucket` 逻辑
- 卡片只保留 `onDoubleClick`（单击无操作）

#### D5: 加「< 返回」按钮 + 标题规则

在 PhotoToolbar 上方或内部加返回按钮：
- 仅在 `state.view === 'all'` 且有 `year`/`month` filter 时显示
- 点击 → 回来源概览（根据 filter 判断回 Years 还是 Months）
  - 有 `month` → 回 Months 概览
  - 只有 `year` → 回 Years 概览

标题规则（传给 PhotoToolbar 的 `title` prop）：
- `view === 'all'` 无 filter：`时间线`
- `view === 'all'` 带 year（无 month）：`YYYY 年`
- `view === 'all'` 带 year+month：`YYYY 年 M 月`
- `view === 'years'`：`年份`
- `view === 'months'`：`月份`

#### D6: 概览图分批加载前端实现

Years/Months 概览图加 IntersectionObserver + sentinel：
- 复用现有无限滚动机制（All Photos 的 sentinel 模式）
- 每次 30 个卡片
- API 调用加 `limit=30&cursor=...` 参数

api.ts 修改：
```tsx
// getTimelineYears 加 limit/cursor 参数
getTimelineYears(limit?: number, cursor?: number): Promise<{
  years: YearData[];
  next_cursor: number | null;
  has_next: boolean;
}>

// getTimelineMonths 加 limit/cursor 参数
getTimelineMonths(year?: number, limit?: number, cursor?: string): Promise<{
  months: MonthData[];
  next_cursor: string | null;
  has_next: boolean;
}>
```

#### D7: All Photos 带 filter 时按天分组

当前 All Photos 已经按天分组（`groupPhotosByDay` 函数）。确认带 year/month filter 时也按天分组即可，应该无需改。

**验证**：
- `npm run build` 无编译错误
- 3 个 tab（All Photos / Months / Years）
- 双击 Years 卡片 → All Photos（带 year filter）
- 双击 Months 卡片 → All Photos（带 year+month filter）
- 返回按钮回到来源概览
- 概览图选择按钮禁用

---

### 任务 E：构建验证

**目标**：全部改完后构建验证 + MCP 验证。

**依赖**：A+B+C+D 全部完成。

**步骤**：
1. `cd frontend && npm run build` 无编译错误
2. 启动应用 `python src/BlurArc.py`
3. MCP 验证：
   - Timeline 3 个 tab 切换正常
   - 双击 Years/Months 卡片进 All Photos
   - 返回按钮回来源概览
   - 选择模式 banner 按钮生效（全选/删除/加入相册）
   - 筛选/排序 modal 弹窗正常
4. 写 devlog 到 `docs/devlogs/2026-06-27-timeline-apple-photos-refactor.md`

---

## 4. 执行计划

### 第一波（并行执行 3 个 subagent）

| Subagent | 任务 | 预计文件 |
|----------|------|----------|
| Subagent 1 | 任务 A（后端 API） | api_server.py, database.py |
| Subagent 2 | 任务 B（App.tsx 回调） | App.tsx |
| Subagent 3 | 任务 C（筛选/排序 UI） | FilterMenu.tsx, SortMenu.tsx, PhotoToolbar.tsx |

### 第二波（1 个 subagent）

| Subagent | 任务 | 预计文件 |
|----------|------|----------|
| Subagent 4 | 任务 D（TimelineView 重构） | TimelineView.tsx, api.ts |

### 第三波（手动或 subagent）

| 执行者 | 任务 |
|--------|------|
| 主 agent | 任务 E（构建验证 + MCP + devlog） |

## 5. 风险与注意事项

1. **任务 C 和 D 都改 PhotoToolbar.tsx**：
   - C 改 FilterMenu/SortMenu 调用方式
   - D 不改 PhotoToolbar（只改 TimelineView）
   - 无冲突，可并行

2. **任务 D 依赖 A 的 API**：
   - D5（分批加载）需要 A2/A3 的 limit/cursor 参数
   - 如果 A 未完成，D5 可以先用 mock 数据，后续联调

3. **任务 B 和 D 都涉及 App.tsx**：
   - B 改 `<TimelineView>` 的 props
   - D 不改 App.tsx（只改 TimelineView.tsx）
   - 无冲突

4. **构建验证**：
   - 每个任务完成后可单独 `npm run build` 验证编译
   - 完整 MCP 验证在第三波统一做

---

## 6. 验收标准

> **总原则**：所有项目必须 100% 通过。每项可独立验证（是/否），不通过则返工。

### A. 后端 API（任务 A）

- [ ] **A-1** `/api/timeline/photos?year=2024` 返回 2024 年所有照片（不报错，返回数组）
- [ ] **A-2** `/api/timeline/photos?year=2024&month=8` 返回 2024-08 所有照片
- [ ] **A-3** `/api/timeline/photos`（无参数）返回所有照片
- [ ] **A-4** `/api/timeline/years?limit=10` 返回最多 10 个年份 + `next_cursor` + `has_next` 字段
- [ ] **A-5** `/api/timeline/years?limit=10&cursor=2020` 返回 2020 年之前的年份
- [ ] **A-6** `/api/timeline/months?limit=10` 返回最多 10 个月份 + `next_cursor` + `has_next`
- [ ] **A-7** `/api/timeline/months?limit=10&cursor=2024-02` 返回 2024-02 之前的月份
- [ ] **A-8** 不传 limit/cursor 时 API 仍兼容（返回全部，无 next_cursor 或 has_next=false）
- [ ] **A-9** `/api/timeline/days` API 保留且仍可访问（不破坏兼容）

### B. App.tsx 回调（任务 B）

- [ ] **B-1** App.tsx 中 `<TimelineView>` 传了 `onSelectAll` prop
- [ ] **B-2** App.tsx 中 `<TimelineView>` 传了 `onDeleteSelected` prop
- [ ] **B-3** App.tsx 中 `<TimelineView>` 传了 `onJoinAlbums` prop
- [ ] **B-4** Timeline 视图进入选择模式后，点「全选」按钮能选中当前所有照片
- [ ] **B-5** Timeline 视图选中照片后，点「删除」按钮触发删除对话框
- [ ] **B-6** Timeline 视图选中照片后，点「加入相册」按钮触发加入相册弹窗
- [ ] **B-7** Timeline 视图点「取消」退出选择模式

### C. 筛选/排序 UI（任务 C）

- [ ] **C-1** 点工具栏「筛选」按钮 → 弹出居中 modal 弹窗（不是下拉菜单）
- [ ] **C-2** 点工具栏「排序」按钮 → 弹出居中 modal 弹窗
- [ ] **C-3** 筛选 modal 有 4 个选项（photo/video/favorite/not_in_album）
- [ ] **C-4** 筛选 modal 选项样式对齐原型图（左 icon + label + 右 ✓）
- [ ] **C-5** 点筛选选项 → toggle 选中状态（多选），不关闭 modal
- [ ] **C-6** 点 modal 外 mask 区域 → 关闭筛选 modal
- [ ] **C-7** 排序 modal 选项样式与筛选一致
- [ ] **C-8** 点排序选项 → 选中并关闭 modal（单选）
- [ ] **C-9** MainContent 和 TimelineView 两个视图的筛选/排序 modal 行为一致（公用组件）

### D. TimelineView 重构（任务 D）

#### D-1. 顶部 Tab

- [ ] **D-1** Timeline 顶部只有 3 个 tab（All Photos / Months / Years）
- [ ] **D-2** 没有 Days tab
- [ ] **D-3** 默认显示 All Photos 视图

#### D-2. 双击行为

- [ ] **D-4** Years 概览图双击某年卡片 → 进入 All Photos（显示该年照片）
- [ ] **D-5** Months 概览图双击某月卡片 → 进入 All Photos（显示该月照片）
- [ ] **D-6** All Photos 视图双击照片 → 进入照片预览（不变）
- [ ] **D-7** Years/Months 概览图卡片**单击**无操作（不跳转、不高亮）

#### D-3. 标题与返回

- [ ] **D-8** All Photos（无 filter）标题为「时间线」
- [ ] **D-9** All Photos（带 year）标题为「YYYY 年」（如「2024 年」）
- [ ] **D-10** All Photos（带 year+month）标题为「YYYY 年 M 月」
- [ ] **D-11** Years 概览标题为「年份」
- [ ] **D-12** Months 概览标题为「月份」
- [ ] **D-13** All Photos（带 filter）时显示「< 返回」按钮
- [ ] **D-14** All Photos（无 filter）时不显示「< 返回」按钮
- [ ] **D-15** Years/Months 概览时不显示「< 返回」按钮
- [ ] **D-16** 从 All Photos（带 year+month）点返回 → 回到 Months 概览
- [ ] **D-17** 从 All Photos（仅带 year）点返回 → 回到 Years 概览
- [ ] **D-18** 点顶部 tab 切换视图时清空 filter 和返回路径

#### D-4. 选择模式

- [ ] **D-19** All Photos 视图下「选择」按钮可点
- [ ] **D-20** Years/Months 概览下「选择」按钮禁用（灰色不可点）
- [ ] **D-21** 选择模式下切到概览图 → 自动退出选择模式
- [ ] **D-22** 选择模式下显示 SelectionBanner（全选/加入相册/删除/取消按钮）

#### D-5. 分批加载

- [ ] **D-23** Years 概览图卡片数 > 30 时分批加载（首屏 30 个）
- [ ] **D-24** Years 概览图滚动到底部 → 加载下一批
- [ ] **D-25** Months 概览图卡片数 > 30 时分批加载
- [ ] **D-26** Months 概览图滚动到底部 → 加载下一批
- [ ] **D-27** 分批加载有 loading 指示（如骨架屏或 spinner）
- [ ] **D-28** 所有卡片加载完后不再触发加载

#### D-6. All Photos 按天分组

- [ ] **D-29** All Photos（无 filter）按天分组显示照片
- [ ] **D-30** All Photos（带 year filter）按天分组显示该年照片
- [ ] **D-31** All Photos（带 year+month filter）按天分组显示该月照片

### E. 整体验收

- [ ] **E-1** `cd frontend && npm run build` 无编译错误
- [ ] **E-2** `python src/BlurArc.py` 启动应用无报错
- [ ] **E-3** 旧版本用户升级后数据不丢失（数据库 schema 不破坏）
- [ ] **E-4** MainContent（文件夹/收藏/相册）视图不受影响，功能正常
- [ ] **E-5** 其他 view（Favorites/Albums/Folders）不受影响
- [ ] **E-6** devlog 写到 `docs/devlogs/2026-06-27-timeline-apple-photos-refactor.md`

---

## 7. 验收执行流程

1. 每个任务完成后，对应分组逐项打勾
2. 全部任务完成后，执行 E 组整体验收
3. 任一项不通过 → 返工对应任务
4. 全部通过 → 本次重构完成，可提交 git
