# 2026-06-27 Timeline 交互重构：对齐 Apple Photos（3 tab + 双击 + 返回）

## 背景

原 Timeline 视图有 4 个 tab（所有照片/日/月/年），单击卡片逐级下钻（年→月→日→所有照片），交互繁琐且与 Apple Photos 不一致。

调研 Apple Photos 官方文档（Tahoe 最新版）后确认：
- 只有 3 个 tab（Years / Months / All Photos），**已移除 Days**
- 双击卡片直接进入 All Photos（带 filter）
- 按天分组在 All Photos 视图内完成

确定**方案 X**：3 tab + 双击直接进 All Photos（带 filter）+ 按天分组 + 返回按钮。

同时顺带完成两项公共组件对齐：
- **筛选/排序 UI**：下拉菜单 → modal 弹窗（与原型图一致）
- **PhotoToolbar/SelectionBanner 公共化**：TimelineView 复用 MainContent 的工具栏与 banner 组件

## 方案与实施文档

| 文档 | 路径 |
|------|------|
| 方案文档 | [docs/superpowers/specs/2026-06-27-timeline-apple-photos-redesign.md](../superpowers/specs/2026-06-27-timeline-apple-photos-redesign.md) |
| 实施文档 | [docs/superpowers/plans/2026-06-27-timeline-implementation-plan.md](../superpowers/plans/2026-06-27-timeline-implementation-plan.md) |
| 原 spec | [docs/superpowers/specs/2026-06-24-v0.7-album-ui-spec.md](../superpowers/specs/2026-06-24-v0.7-album-ui-spec.md)（§4.4 更新） |
| 原型图 | [docs/prototypes/desktop/album-management-v2-light.html](../prototypes/desktop/album-management-v2-light.html) |

## 改动清单

### 后端（任务 A）

[backend/api_server.py](../../backend/api_server.py)：
- `/api/timeline/years`：加 `limit`/`cursor` 分批参数，响应加 `next_cursor`/`has_next`
- `/api/timeline/months`：加 `limit`/`cursor` 分批参数，cursor 格式 `"YYYY-MM"`
- `/api/timeline/photos`：`year`/`month`/`day` 三参数已全部可选，无需改
- `/api/timeline/days`：保留不动（前端不再调用，但 API 不删）

### 前端（任务 B/C/D）

| 文件 | 改动 |
|------|------|
| [frontend/src/App.tsx](../../frontend/src/App.tsx) | 补传 TimelineView 的 `onSelectAll`/`onDeleteSelected`/`onJoinAlbums` 三个回调 |
| [frontend/src/components/common/FilterMenu.tsx](../../frontend/src/components/common/FilterMenu.tsx) | 下拉菜单 → modal 弹窗（mask + 卡片 360px），新增 `onClose` prop，多选不关闭 |
| [frontend/src/components/common/SortMenu.tsx](../../frontend/src/components/common/SortMenu.tsx) | 同上 modal-mask 结构，单选选完即关 |
| [frontend/src/components/common/PhotoToolbar.tsx](../../frontend/src/components/common/PhotoToolbar.tsx) | 去掉筛选/排序按钮外层 `relative` 包裹，FilterMenu 补 `onClose` |
| [frontend/src/components/timeline/TimelineView.tsx](../../frontend/src/components/timeline/TimelineView.tsx) | 整体重写（419 行） |
| [frontend/src/services/api.ts](../../frontend/src/services/api.ts) | `getTimelineYears`/`getTimelineMonths` 加分批参数，删除 `getTimelineDays` |
| [frontend/src/contexts/I18nContext.tsx](../../frontend/src/contexts/I18nContext.tsx) | 新增 `timeline.yearsTitle`/`timeline.monthsTitle` |

### TimelineView 关键改动（任务 D）

| 编号 | 改动 |
|------|------|
| D1 | `TimelineViewType = 'all' \| 'months' \| 'years'`（去掉 `'days'`） |
| D2 | 删除 days 视图代码、days API 调用、Days tab、day state |
| D3 | Years/Months 卡片 `onDoubleClick` 直接进 `view: 'all'` 带 year/month filter |
| D4 | 删除 `selectedBucket` state（单击无操作） |
| D5 | 新增「< 返回」按钮 + 标题规则（时间线/YYYY 年/YYYY 年 M 月/年份/月份） |
| D6 | Years/Months 分批加载（PAGE_SIZE=30，IntersectionObserver + sentinel） |
| D7 | All Photos 按天分组（复用 `groupPhotosByDay`） |
| D18 | 切 tab 清空 filter 和返回路径 |
| D21 | 选择模式下切到概览自动退出选择模式 |

### Spec 与原型图

- [docs/superpowers/specs/2026-06-24-v0.7-album-ui-spec.md](../superpowers/specs/2026-06-24-v0.7-album-ui-spec.md) §4.4：4 tab → 3 tab，Days 视图整段删除，Months/Years 双击直接进 All Photos
- [docs/prototypes/desktop/album-management-v2-light.html](../prototypes/desktop/album-management-v2-light.html)：HTML view-tabs 去 Days，卡片 onclick → ondblclick，renderTimelineAll 加 filter 按天分组

## 关键代码

### TimelineView 标题规则与返回按钮

```tsx
// D5: 标题规则
const title = state.view === 'all'
  ? (state.year && state.month
      ? t('timeline.yearMonthLabel', { year: state.year, month: state.month })
      : state.year
        ? t('timeline.yearLabel', { year: state.year })
        : t('sidebar.timeline'))
  : state.view === 'years'
    ? t('timeline.yearsTitle')
    : t('timeline.monthsTitle');

// D5: 返回按钮仅 All Photos 带 filter 时显示
const showBack = state.view === 'all' && (state.year !== undefined || state.month !== undefined);
const handleBack = () => {
  if (selectionMode) onSelect?.();
  if (state.month) {
    setState({ view: 'months', year: state.year });  // 带 year+month → 回 Months
  } else if (state.year) {
    setState({ view: 'years' });  // 仅 year → 回 Years
  }
};
```

### FilterMenu modal 结构

```tsx
<div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={onClose}>
  <div className="bg-card rounded-lg shadow-xl w-[360px] p-4" onClick={e => e.stopPropagation()}>
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-[15px] font-semibold">{t('common.filter')}</h3>
      <button onClick={onClose} className="...">×</button>
    </div>
    {filterOptions.map(opt => (
      <button
        key={opt.key}
        onClick={() => onToggle(opt.key)}
        className="w-full flex items-center gap-3 px-4 py-2 ..."
      >
        <span className="w-5 text-center text-sm text-text-secondary">{opt.icon}</span>
        <span>{opt.label}</span>
        <span className={`ml-auto text-primary ${selected.includes(opt.key) ? 'opacity-100' : 'opacity-0'}`}>✓</span>
      </button>
    ))}
  </div>
</div>
```

## 验收结果

构建通过（`npm run build` ✅），应用启动正常。通过 Chrome DevTools MCP 验证全部验收项：

| 验收项 | 结果 |
|--------|------|
| D-1/D-2/D-3：3 个 tab（所有照片/月/年），无 Days tab | ✅ |
| D-11：Years 概览标题"年份" | ✅ |
| D-12：Months 概览标题"月份" | ✅ |
| D-15：概览无返回按钮 | ✅ |
| D-20：概览下选择按钮禁用 | ✅ |
| D-4：双击 Years 卡片 → All Photos（带 year filter） | ✅ |
| D-9：标题"2026年" | ✅ |
| D-13：带 filter 时显示返回按钮 | ✅ |
| D-19：All Photos 下选择按钮可点 | ✅ |
| D-30：带 year filter 按天分组 | ✅ |
| D-17：点返回 → 回 Years 概览 | ✅ |
| D-5：双击 Months 卡片 → All Photos（带 year+month filter） | ✅ |
| D-10：标题"2026年6月" | ✅ |
| D-16：点返回 → 回 Months 概览（保留 year） | ✅ |
| C-1~C-4：筛选 modal（mask + 标题 + × + 4 选项 + icon+label+✓） | ✅ |
| C-5：多选不关闭 | ✅ |
| C-6：toggle ✓ 可见性（opacity-0/100） | ✅ |
| C-7：排序 modal（同结构） | ✅ |
| C-8：单选选完即关 | ✅ |
| C-9：点 × 关闭 | ✅ |
| B-4~B-7：SelectionBanner（已选 N 张/全选/加入相册/删除/取消，无"从相册移除"） | ✅ |
| 全选 → 86 张，按钮变"取消全选" | ✅ |
| E-4：MainContent（我的收藏）正常显示，无 View Tabs/返回按钮 | ✅ |
| E-5：MainContent 选择模式 banner 正常 | ✅ |

## 遇到的问题

1. **TS2322 类型错误**：TimelineView 的 `onSelect` 是可选 prop，但 PhotoToolbar 要求必填。修复：`onSelect={onSelect || (() => {})}`。

2. **MCP 双击触发**：React 的 `onDoubleClick` 是合成事件，原生 `ondblclick` 属性为 false。需用 `dispatchEvent(new MouseEvent('dblclick', {bubbles:true}))` 触发，且要选对卡片元素（`.grid > div`）。

3. **a11y tree 误判**：snapshot 中所有 FilterMenu 选项都显示 ✓，但实际 `opacity-0` 不可见。需用 `evaluate_script` 检查 className 确认真实选中状态。

## 涉及文件总览

| 类别 | 文件 |
|------|------|
| 后端 | backend/api_server.py |
| 前端组件 | frontend/src/components/timeline/TimelineView.tsx, frontend/src/components/common/FilterMenu.tsx, frontend/src/components/common/SortMenu.tsx, frontend/src/components/common/PhotoToolbar.tsx |
| 前端服务 | frontend/src/services/api.ts |
| 前端入口 | frontend/src/App.tsx |
| 前端 i18n | frontend/src/contexts/I18nContext.tsx |
| Spec | docs/superpowers/specs/2026-06-24-v0.7-album-ui-spec.md |
| 新方案 | docs/superpowers/specs/2026-06-27-timeline-apple-photos-redesign.md, docs/superpowers/plans/2026-06-27-timeline-implementation-plan.md |
| 原型图 | docs/prototypes/desktop/album-management-v2-light.html |
