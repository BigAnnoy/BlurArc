# 2026-06-26 MCP 浏览器端到端回归测试

## 背景
用户在 2026-06-22 后报过 7 个 bug 并完成修复（见 [devlog](2026-06-21-upload-bug-fixes.md) 等）。本次按用户要求"检查各按钮 + MCP 跑一遍"，用 Chrome DevTools MCP 模拟真实用户操作，回归验证修复效果并发现新问题。

## 测试环境
- 后端：`python -m backend.api_server`（端口 5000，SQLite db）
- 前端：`vite dev`（端口 5173，代理 `/api` → 5000）
- 浏览器：MCP 控制 Chrome，访问 `http://127.0.0.1:5173/`

## 发现并已修复的问题

### Bug A：时间线日视图空白（高严重）

**症状**：进入时间线 → 月视图 → 6月 → 23日，photo grid 只有 1 张（实际 23 日有 2 张照片）。

**根因**：[backend/api_server.py](backend/api_server.py) `get_timeline_photos` 中 `func.date(Photo.media_date) == day` 在 SQLite 下不工作 —— `'23'` 是 string，`date(...)` 返回 date 类型，二者比较永远不匹配。

**修复**：
```python
# 旧（坏）
query = query.filter(func.date(Photo.media_date) == day)

# 新（好）— 比较 day-of-month 数字
day_clean = day.lstrip('0') or '0'
query = query.filter(func.cast(func.strftime('%d', Photo.media_date), Integer) == int(day_clean))
```

同时补上 `from sqlalchemy import ... Integer` import。

**验证**：`GET /api/timeline/photos?year=2026&month=6&day=23` → 2 张照片。

### Bug B：PhotoPreview 显示 "1 / 0"（高严重）

**症状**：在时间线日详情点开图，PhotoPreview 顶栏显示 `1 / 0`（分母为 0，应为 2）。

**根因**：[frontend/src/components/dialogs/PhotoPreview.tsx](frontend/src/components/dialogs/PhotoPreview.tsx) 用 `photos={state.photos}` 做总数。但 `App.tsx` 在切换到时间线视图时把 `state.photos` 清空（[App.tsx:181](frontend/src/App.tsx#L181)），时间线视图内部自己维护的 photos 数组未同步给 App。

**修复（双保险）**：
1. **PhotoPreview 加 fallback**：`const photosList = photos && photos.length > 0 ? photos : (photo ? [photo] : []);`，所有 `photos.length` / `photos[i]` 改用 `photosList`。
2. **TimelineView 同步 photos 给 App**：新增 `onPhotosChange` prop，在 setPhotos 后回调：
   ```typescript
   onPhotosChange?.(res.photos.map(p => ({ id: String(p.id), name: p.filename, ... })));
   ```
3. **App.tsx** 传 `onPhotosChange={(photos) => setState(prev => ({ ...prev, photos }))}`。

**验证**：MCP 中打开 23 日第 1 张图 → PhotoPreview 显示 `1 / 2`，键盘 → 切到 `2 / 2`，键盘 ← 切回 `1 / 2`。

### Bug C：后端进程冲突导致 API 走旧版本

**症状**：重启后浏览器仍看到所有 stats=0，timeline 数据加载不到。

**根因**：`taskkill /F /IM python.exe` 没杀干净，5000 端口被旧版本实例占着。

**修复**：手工 `taskkill /F /IM python.exe /T` 后用 `python -m backend.api_server` 启动新实例，确认 `Running on http://127.0.0.1:5000`。

### Bug D：时间线日详情分组错乱（中等严重）

**症状**：日详情视图下，同一天的多张照片被分成 2 个 group（如 23 日有 2 张照片显示成 "2026年6月23日 (1 张) 屏幕截图… + 2026年6月23日 (1 张) 屏幕截图…"）。

**根因**：[TimelineView.tsx:68](frontend/src/components/timeline/TimelineView.tsx#L68) `groupPhotosByDay` 用 `photo.date.split(' ')[0]` 取日期部分。但后端返回的 `date` 是 ISO 格式（`2026-06-23T17:56:58`），不含空格 —— split 之后返回整个 ISO 字符串，每张照片时间戳不同 → 不同 key → 不同 group。

**修复**：用 `'T'` 切，且兼容空格格式（fallback）：
```typescript
const date = (photo.date || '').split('T')[0] || (photo.date || '').split(' ')[0];
```

**验证**：日详情下 23 日两张照片合并为 1 个 group "2026年6月23日 (2 张)"。

## MCP 测试技巧记录

### 模拟 React 组件点击的可靠方法
- **首选**：`card.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window, button: 0 }))` 模拟 native click
- **键盘**：`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))`
- **不靠谱**：`card.click()` 直接调 native method，React 18+ synthetic onClick 偶尔不同步

### 通过网格文本定位子组件
```js
const it = Array.from(grid.children).find(x => x.textContent.includes('6月'));
it.click();
```
比 `children[0]` 健壮（grid 顺序可能变）。

## 待办 / 后续可优化
- [ ] 验证视频缩略图在 PhotoPreview 中显示时长
- [ ] 验证手动排序按钮（按月/按年/全部）在 FolderView 中工作
- [ ] AlbumSidebar 计数显示需 reload 后再确认
- [ ] JoinAlbumModal 多选批处理流程未在 MCP 中点完
- [ ] 后端启动脚本应检测端口占用并提示清理

## 相关文件
- [backend/api_server.py:3342-3353](backend/api_server.py#L3342-L3353) — day filter 修复
- [frontend/src/components/dialogs/PhotoPreview.tsx:28](frontend/src/components/dialogs/PhotoPreview.tsx#L28) — photosList fallback
- [frontend/src/components/timeline/TimelineView.tsx:104-122](frontend/src/components/timeline/TimelineView.tsx#L104-L122) — onPhotosChange 同步
- [frontend/src/App.tsx:630-633](frontend/src/App.tsx#L630-L633) — onPhotosChange 接收
