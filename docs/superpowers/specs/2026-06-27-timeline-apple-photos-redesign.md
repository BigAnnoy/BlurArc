# Timeline 交互重构方案（对齐 Apple Photos）

> **状态**：草案，待用户确认
> **日期**：2026-06-27
> **背景**：v0.7 Timeline 概览图交互（双击逐级下钻 + 单击选中高亮 + breadcrumb）与 Apple Photos 习惯有差异，需重构对齐。

## 1. 调研结论（Apple 官方文档）

来源：[Apple Support - Find photos and videos by date on Mac](https://support.apple.com/pa-in/guide/photos/pht56eafa987/11.0/mac/27)（macOS Tahoe 26 最新版）

| 项 | Apple Photos 实际行为 |
|------|------|
| toolbar 选项 | **3 个**：Years / Months / All Photos（最新版已移除 Days） |
| 进入下一级 | **双击**卡片 |
| 触控板 | 支持 pinch open/closed 切换层级 |
| 返回 | 工具栏「< 返回」按钮 |
| breadcrumb | 无 |
| 选中态 | 概览层级无"单击选中"概念 |

**官方文档原文**：
> "In the toolbar, click one of the following: Years / Months / All Photos. Double-click a month or year to see the photos in it."

**注意**：文档说"Double-click ... to see the photos in it"，未明说是跳下一级视图还是直接显示照片列表。结合 macOS Tahoe 移除 Days tab 的事实，推断最新版行为是**双击直接进 All Photos（带时间 filter）**。

## 2. 核心设计（方案 X）

### 2.1 顶部 Tab

**3 个 tab**（对齐 Apple Photos Tahoe，去掉 Days）：
- **All Photos**：所有照片按天分组显示
- **Months**：所有月份概览图（跨年份）
- **Years**：所有年份概览图

### 2.2 双击行为（直接进 All Photos，不逐级下钻）

| 当前视图 | 双击行为 | 目标 |
|----------|----------|------|
| Years | 双击某年 | → All Photos（带 `year` filter，显示整年照片） |
| Months | 双击某月 | → All Photos（带 `year+month` filter，显示整月照片） |
| All Photos | 双击照片 | → 照片预览（不变） |

**关键变化**：不再有 `Years → Months → Days → All Photos` 逐级下钻链。双击任意概览卡片直接进 All Photos。

### 2.3 All Photos 视图展示（带 filter 时按天分组）

- **无 filter**（默认 All Photos tab）：所有照片按天分组显示（每天一个 section header）
- **带 year filter**（从 Years 双击进入）：该年所有照片，按天分组显示
- **带 year+month filter**（从 Months 双击进入）：该月所有照片，按天分组显示

### 2.4 导航与返回

- **「< 返回」按钮**：drill-down 进入 All Photos（带 filter）时显示，点击回到上一级概览
- **顶部 tab**：点 tab 直接跳顶层视图（清空 drill-down 路径）
- **标题规则**：
  - All Photos（无 filter）：`时间线`
  - All Photos（带 year）：`YYYY 年`
  - All Photos（带 year+month）：`YYYY 年 M 月`
  - Years 概览：`年份`
  - Months 概览：`月份`

### 2.5 概览图选择模式

- 概览图视图（Years/Months）下**禁用选择按钮**（灰色，不可点）
- 仅 All Photos 视图支持选择模式
- 用户在选择模式下切到概览图 → 自动退出选择模式

### 2.6 概览图分批加载

- Years/Months 概览图加 `limit=30` + `cursor` 分批加载
- 使用 IntersectionObserver + sentinel 模式（复用现有无限滚动机制）
- API 加 `next_cursor` 和 `has_next` 字段

## 3. 完整改动清单

### 3.1 spec 文档（[2026-06-24-v0.7-album-ui-spec.md](file:///f:/AI/Frame_Album/docs/superpowers/specs/2026-06-24-v0.7-album-ui-spec.md)）

| 位置 | 改动 |
|------|------|
| §4 核心交互描述 | 改为"3 tab + 双击直接进 All Photos（带 filter）+ 按天分组" |
| §4.4 View Tabs | 4 tab → **3 tab**（去掉 Days） |
| §4.4.2 Days 视图 | **整段删除** |
| §4.4.3 Months 视图 | 双击某月 → All Photos（带 `year+month` filter） |
| §4.4.4 Years 视图 | 双击某年 → All Photos（带 `year` filter） |
| §4.4.5 导航栈 | 简化：双击直接进 All Photos；「< 返回」回 Years/Months 概览 |
| §4.6.1 通用行为 | 回滚为"双击 drill down"（v0.7.1 草案误改成单击） |
| §4.6.2 drill down | Years/Months 双击都直接 → All Photos（不再逐级） |
| §4.6.3 分批加载 | 去掉 Days API 分批描述；Years/Months 保留 |
| §11.2 验收清单 | 更新双击行为 + 去掉 Days 验收项 + 加"看整月/整年照片" |

### 3.2 原型图（[album-management-v2-light.html](file:///f:/AI/Frame_Album/docs/prototypes/desktop/album-management-v2-light.html)）

| 改动点 | 说明 |
|------|------|
| HTML view-tabs | 去掉 Days tab（4 → 3） |
| `switchTlTab` | 去掉 `'days'` case |
| `renderTimelineOverview` | 去掉 days 分支；Years/Months 卡片改 `ondblclick` → 直接进 All Photos |
| `drillDownTimeline` | target 只能是 `{tab: 'all', year, month?}` |
| `updateTimelineHeader` | 简化标题规则（无 days 层级） |
| 卡片 `onclick` → `ondblclick` | 回滚为双击（v0.7.1 草案误改成单击） |
| 选择按钮禁用逻辑 | 保留（概览图视图下禁用） |
| All Photos 按天分组 | 加 mock 展示带 filter 时按天分组的效果 |

### 3.3 前端代码

| 文件 | 改动 |
|------|------|
| [TimelineView.tsx](file:///f:/AI/Frame_Album/frontend/src/components/timeline/TimelineView.tsx) | `TimelineViewType` 去掉 `'days'`；删除 days 视图代码；Years/Months `onDoubleClick` → 直接 `setState({view: 'all', year, month?})`；不再逐级下钻；回滚单击为双击 |
| [App.tsx](file:///f:/AI/Frame_Album/frontend/src/App.tsx) | 补传 TimelineView 批量操作回调（`onSelectAll`/`onDeleteSelected`/`onJoinAlbums`）—— 公用组件化收尾（详见 §3.3.1） |
| [api.ts](file:///f:/AI/Frame_Album/frontend/src/services/api.ts) | `getTimelinePhotos` 确认支持只传 `year`（看整年）或 `year+month`（看整月） |
| [FilterMenu.tsx](file:///f:/AI/Frame_Album/frontend/src/components/common/FilterMenu.tsx) / [SortMenu.tsx](file:///f:/AI/Frame_Album/frontend/src/components/common/SortMenu.tsx) | 重构对齐原型图（详见 §3.3.2） |

### 3.3.1 公用组件化（PhotoToolbar + SelectionBanner）

**现状**：

| 组件 | 状态 | 说明 |
|------|------|------|
| [PhotoToolbar.tsx](file:///f:/AI/Frame_Album/frontend/src/components/common/PhotoToolbar.tsx) | ✅ 已建好 | 含布局切换/缩放/筛选/排序/选择按钮；选择模式下隐藏工具按钮；支持 `actionsDisabled` |
| [SelectionBanner.tsx](file:///f:/AI/Frame_Album/frontend/src/components/common/SelectionBanner.tsx) | ✅ 已建好 | 含取消/全选/加入相册/从相册移除/删除按钮；`onJoinAlbums`/`onRemoveFromAlbum` 可选 |
| [MainContent.tsx](file:///f:/AI/Frame_Album/frontend/src/components/layout/MainContent.tsx) | ✅ 已替换 | 使用 PhotoToolbar + SelectionBanner |
| [TimelineView.tsx](file:///f:/AI/Frame_Album/frontend/src/components/timeline/TimelineView.tsx) | ✅ 已替换 | 使用 PhotoToolbar + SelectionBanner |
| [App.tsx](file:///f:/AI/Frame_Album/frontend/src/App.tsx) | ❌ 未补传回调 | TimelineView 缺 `onSelectAll`/`onDeleteSelected`/`onJoinAlbums`，banner 按钮空操作 |
| 构建验证 | ❌ 未执行 | 需 `npm run build` 验证 |

**待完成**：

1. **App.tsx 补传 TimelineView 批量操作回调**（复用 MainContent 的同名 handler）：
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
2. `npm run build` 验证无编译错误
3. MCP 验证 PhotoToolbar + SelectionBanner 在 MainContent 和 TimelineView 两个视图都正常工作

### 3.3.2 筛选/排序 UI 对齐原型图

**现状对比**：

| 项 | 当前代码（[FilterMenu.tsx](file:///f:/AI/Frame_Album/frontend/src/components/common/FilterMenu.tsx) / [SortMenu.tsx](file:///f:/AI/Frame_Album/frontend/src/components/common/SortMenu.tsx)） | 原型图（[album-management-v2-light.html](file:///f:/AI/Frame_Album/docs/prototypes/desktop/album-management-v2-light.html) 行 700-716, 1650-1668, 2060-2185） |
|------|------|------|
| 形式 | **下拉菜单**（`absolute right-0 top-full`，附在按钮下方） | **modal 弹窗**（`modal-mask` 居中卡片） |
| 分隔线 | ❌ 无 | ✅ `.filter-sep`（`height: 1px; background: var(--border); margin: 6px 0`） |
| 选项数 | 4 个（photo/video/favorite/not_in_album） | 7-10 个（含截屏/已编辑/关键词/时间范围） |
| 样式 | 简单 list（`px-3 py-2`） | `.filter-item`（全宽 + `.fi-icon` 20px + `.fi-check` 自动右对齐） |
| 关闭方式 | 需手动管理 state | `modal-mask` 点击关闭 + `closeModal()` |

**原型图选项集**（按 view 区分）：
- `timeline`：全部照片/已收藏/视频/截屏/已编辑 + 分隔线 + 今年/去年
- `favorites`：全部收藏/仅照片/仅视频 + 分隔线 + 最近 7 天/30 天/一年
- `album`：全部/仅照片/仅视频 + 分隔线 + 已收藏/已编辑
- `tree`：全部/照片/视频/已收藏/截屏/已编辑 + 分隔线 + 不在相册中 + 分隔线 + 关键词

**待完成**：

1. **FilterMenu.tsx 重构**：
   - 形式：下拉菜单 → modal 弹窗（复用 `modal-mask` 模式）
   - 加分隔线支持（`{ type: 'sep' }` 选项）
   - 样式对齐 `.filter-item` / `.fi-icon` / `.fi-check`
2. **SortMenu.tsx 同步重构**（复用 `.filter-item` 样式）
3. **选项扩展**（需后端 API 支持）：
   - 加截屏（screenshots）/已编辑（edited）筛选
   - 加时间范围（最近 7 天/30 天/一年）
4. **后端 API 扩展**：`/api/timeline/photos` 和 `/api/photos` 的 `filters` 参数加 `screenshots`/`edited`/`time_range` 支持

**决策点**（待确认）：
- 形式：保留下拉菜单（轻量）vs 改为 modal 弹窗（对齐原型图）？
- 选项扩展：本期全做 vs 只对齐样式，选项扩展后做？

### 3.4 后端代码

| 文件 | 改动 |
|------|------|
| [api_server.py](file:///f:/AI/Frame_Album/backend/api_server.py) `/api/timeline/photos` | 确认支持只传 `year`（不传 month/day）→ 返回整年照片；只传 `year+month` → 返回整月照片 |
| `/api/timeline/days` | API 保留（可能其他地方用），但 Timeline 前端不再调用 |
| `/api/timeline/years` `/api/timeline/months` | 加 `limit`/`cursor` 分批参数（§4.6.3） |

## 4. 执行计划（分两步）

### 第一步：spec + 原型图（待方案确认后执行）

1. spec 方案 X 改动（§4.4 / §4.4.2-5 / §4.6 / §11.2）
2. 原型图方案 X 改动（去 Days tab + 双击 + 标题规则 + All Photos 按天分组 mock）
3. 原型图筛选/排序 UI 检查，对齐 spec

**验证点**：用户在浏览器验证原型图交互是否符合预期。

### 第二步：代码改动（待第一步验证后执行）

1. TimelineView 代码重构（去 Days + 双击进 All Photos + 按天分组）
2. App.tsx 补传 TimelineView 批量操作回调（公用组件化收尾）
3. 后端 API 调整（`/api/timeline/photos` 支持 year/month filter）
4. 筛选/排序 UI 代码对齐原型图
5. 概览图分批加载实现

## 5. 决策记录

| 决策点 | 选择 | 理由 |
|--------|------|------|
| drill down 触发方式 | **双击** | 对齐 Apple Photos 官方文档 |
| 顶部 tab 数量 | **3 个**（去掉 Days） | 对齐 Apple Photos Tahoe 最新版 |
| 双击后跳哪 | **直接进 All Photos（带 filter）** | 支持"看整月/整年照片"场景 |
| All Photos 带 filter 时展示 | **按天分组显示** | 便于定位某天，对齐 Apple |
| breadcrumb | **去掉**，用「< 返回」+ 标题 | 对齐 Apple Photos |
| 概览图分批加载 | **本期实现** | 避免大库卡顿 |
| 单击选中高亮 | **去掉** | Apple Photos 概览层级无此概念 |
| 改动范围 | **分两步** | 先 spec + 原型图验证，再改代码 |
| 筛选/排序 UI 形式 | **改为 modal 弹窗** | 对齐原型图 Apple Photos 风格 |
| 筛选选项扩展 | **只对齐样式，不扩展新选项** | 减少本期工作量，截屏/已编辑/时间范围等后做 |

## 6. 待确认

- 方案 X 核心设计是否 OK？
- 完整改动清单是否有遗漏？
- 执行计划（分两步）是否 OK？
