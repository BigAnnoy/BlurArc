# P1 性能修复计划 — 后端 I/O 与缓存优化

**日期**：2026-06-29
**优先级**：P1（资源浪费，但不立即影响用户体验）
**状态**：待实施

---

## 影响面分析

### 修复 4：导入检查合并为单次遍历

**涉及文件**：
- `backend/api_server.py` L1490-1519（修改 `_perform_import_check` 函数）

**调用链**：
```
前端 ImportDialog.tsx
  → api.checkImportAsync() (api.ts)
    → POST /api/import/check-async (api_server.py)
      → _perform_import_check() (api_server.py L1490)
        → os.walk() 两次（当前）
```

**当前逻辑**：
```python
# L1490: 第一次遍历，统计文件总数
all_files_total = sum(len(files) for _, _, files in os.walk(source_path))

# L1519: 第二次遍历，处理文件
for root, _, files in os.walk(source_path):
    for filename in files:
        ...
```

**数据流变化**：
- **当前**：遍历目录两次（第一次统计总数，第二次处理文件）
- **修改后**：遍历目录一次（动态统计进度）

**关键约束**：
- 必须保持进度条推进逻辑（0% → 50% → 100%）
- 必须保持 `all_files_total` 的语义（用于进度计算）
- 必须保持 `media_files` 列表的构建逻辑

**影响范围**：
- 仅影响导入检查的性能
- 不影响导入执行（`_perform_import`）
- 不影响其他导入相关 API

**反例清单**（不应该做的修改）：
- ❌ 不要改变进度条的推进逻辑（0% → 50% → 100%）
- ❌ 不要删除 `media_files` 列表的构建
- ❌ 不要改变 `all_files_total` 的用途（仍用于进度计算）
- ❌ 不要修改 `_perform_import` 函数（导入执行逻辑）
- ❌ 不要修改其他导入相关 API（如 `/api/import/execute`）

---

### 修复 5：video_metadata 添加缓存

**涉及文件**：
- `backend/api_server.py` L705-771（修改 `video_metadata` 函数）

**调用链**：
```
前端 VideoPlayer.tsx / PhotoPreview.tsx
  → api.getVideoMetadata() (api.ts)
    → GET /api/video/metadata (api_server.py L705)
      → VideoProcessor.extract_metadata() (video_processor.py)
```

**当前逻辑**：
```python
# L733: 每次请求都调用 FFmpeg
metadata = VideoProcessor.extract_metadata(str(file_path))
```

**数据流变化**：
- **当前**：每次请求都执行 FFmpeg 子进程
- **修改后**：首次请求执行 FFmpeg，后续请求从缓存读取

**关键约束**：
- 缓存 key 必须包含 `file_mtime`（文件修改后缓存失效）
- 缓存大小必须有限制（防止内存泄漏）
- 必须保持返回结构一致（`available`、`duration`、`resolution` 等字段）

**影响范围**：
- 影响所有视频元数据请求：
  - 视频预览（VideoPlayer.tsx）
  - 照片详情中的视频信息（PhotoPreview.tsx）
- 不影响视频播放（`/api/video/stream`）
- 不影响缩略图生成

**反例清单**（不应该做的修改）：
- ❌ 不要改变返回结构（字段名、类型）
- ❌ 不要删除 FFmpeg 调用（仍需用于首次提取）
- ❌ 不要缓存视频文件本身（只缓存元数据）
- ❌ 不要修改 `/api/video/stream`（视频播放 API）
- ❌ 不要修改缩略图生成逻辑

---

### 修复 6：App.tsx 状态分离

**涉及文件**：
- `frontend/src/App.tsx`（重构状态管理）
- 可能新增 `frontend/src/stores/appStore.ts`（Zustand store）

**调用链**：
```
App.tsx（当前状态集中）
  → Sidebar.tsx（消费 stats、years、rootDir）
  → MainContent.tsx（消费 photos、loading、currentPage）
  → TimelineView.tsx（消费 photos、loading）
  → PhotoPreview.tsx（消费 previewPhoto）
  → ImportDialog.tsx（消费 importOpen）
  → ... 其他组件
```

**当前状态**（App.tsx L47-66）：
```tsx
const [state, setState] = useState<AppState>({
  initialized: false,
  isFirstRun: false,
  stats: null,
  years: [],
  rootDir: null,
  selectedPath: null,
  selectedTitle: '',
  photos: [],
  loading: true,
  selectionMode: false,
  selectedIds: new Set(),
  totalPhotos: 0,
  currentPage: 1,
  hasMore: false,
  currentView: 'timeline',
  selectedAlbumId: null,
  favoriteCount: 0,
});
```

**数据流变化**：
- **当前**：所有状态在 App.tsx，任何状态变化触发整棵树重渲染
- **修改后**：状态分离到 Zustand store，只有使用到该状态的组件才重渲染

**关键约束**：
- 必须保持所有状态的语义不变
- 必须保持所有回调函数的语义不变
- 必须保持所有 useEffect 的逻辑不变
- 必须保持所有子组件的 props 接口不变

**影响范围**：
- 影响整个应用的状态管理
- 影响所有消费 App.tsx 状态的组件
- 不影响 API 调用逻辑
- 不影响业务逻辑

**反例清单**（不应该做的修改）：
- ❌ 不要改变任何状态的语义（如 `loading` 仍表示加载状态）
- ❌ 不要改变回调函数的签名（如 `handlePhotoClick` 仍接收 Photo 对象）
- ❌ 不要删除任何 useEffect
- ❌ 不要改变子组件的 props 接口
- ❌ 不要修改 API 调用逻辑（api.ts）
- ❌ 不要修改业务逻辑（如导入、删除、收藏等）

---

## 问题清单

### 问题 4：导入检查遍历两次目录

**文件**：`backend/api_server.py` L1490-L1519

**现状**：
```python
# L1490: 第一次遍历，只统计文件总数
all_files_total = sum(len(files) for _, _, files in os.walk(source_path))

# L1519: 第二次遍历，处理文件
for root, _, files in os.walk(source_path):
    for filename in files:
        ...
```

**问题**：源目录有 10000 个文件时，遍历两次 = 20000 次文件系统操作。

**影响**：
- 机械硬盘：额外 ~2-5 秒
- SSD：额外 ~0.5-1 秒
- 网络存储：额外 ~10-30 秒

---

### 问题 5：video_metadata 无缓存

**文件**：`backend/api_server.py` L705-L771

**现状**：
```python
# L733: 每次请求都调用 FFmpeg
metadata = VideoProcessor.extract_metadata(str(file_path))
```

**问题**：每次请求都执行 FFmpeg 子进程提取视频元数据。同一视频的元数据（时长、分辨率、编码）不会变化，应该缓存。

**影响**：
- FFmpeg 调用约 100-500ms
- 用户反复查看同一视频时，每次都等待
- 移动端浏览视频列表时，每个视频都触发一次 FFmpeg

---

### 问题 6：App.tsx 状态过于集中

**文件**：`frontend/src/App.tsx` L47-L66

**现状**：
```tsx
const [state, setState] = useState<AppState>({
  initialized: false,
  isFirstRun: false,
  stats: null,
  years: [],
  rootDir: null,
  selectedPath: null,
  selectedTitle: '',
  photos: [],
  loading: true,
  selectionMode: false,
  selectedIds: new Set(),
  totalPhotos: 0,
  currentPage: 1,
  hasMore: false,
  currentView: 'timeline',
  selectedAlbumId: null,
  favoriteCount: 0,
});
```

**问题**：所有状态都在顶层 App 组件，任何状态变化（如 `loading`、`currentPage`）都会触发整个组件树重渲染。

**影响**：
- 翻页时，Sidebar、Header 等不相关组件也会重渲染
- 选择模式切换时，TimelineView 等不相关视图也会重渲染

**注意**：这个问题与 P0 的 PhotoCard memo 问题相关。即使 PhotoCard 加了 memo，如果 App 状态变化导致 props 重建，memo 仍然无效。

---

## 修复方案

### 修复 4：导入检查合并为单次遍历

**方案**：移除第一次遍历，用动态计算的 `total_files` 作为进度分母。

**改动**：

```python
def _perform_import_check(source_path: Path, progress_callback=None):
    # ... 前面的代码 ...
    
    # 阶段1：扫描源目录（单次遍历）
    emit(0, 'scanning', '开始扫描源目录...')
    
    media_files = []
    total_size = 0
    scanned_files = 0
    total_files_scanned = 0  # 动态统计所有文件（含非媒体）
    
    for root, _, files in os.walk(source_path):
        for filename in files:
            scanned_files += 1
            total_files_scanned += 1
            file_path = Path(root) / filename
            
            if file_path.suffix.lower() in MEDIA_FORMATS:
                try:
                    stat_info = file_path.stat()
                    file_size = stat_info.st_size
                    file_mtime = stat_info.st_mtime
                except OSError:
                    continue
                
                exif_datetime = _get_exif_datetime_fast(file_path)
                total_size += file_size
                media_files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_size,
                    'mtime': file_mtime,
                    'exif_datetime': exif_datetime,
                    'thumbnail_url': f'/api/album/thumbnail?path={urllib.parse.quote(str(file_path))}'
                })
            
            # 动态进度：假设媒体文件占比约 30%，估算总进度
            # 实际进度 = 已扫描文件 / 预估总文件数
            estimated_total = max(total_files_scanned, len(media_files) * 3)
            if estimated_total > 0:
                stage_progress = int((scanned_files / estimated_total) * 50)
                emit(min(49, stage_progress), 'scanning', f'扫描中... {scanned_files} 个文件')
    
    emit(50, 'scanning', f'扫描完成，发现 {len(media_files)} 个媒体文件')
    
    # ... 后续代码不变 ...
```

**关键细节**：
- 移除 `all_files_total = sum(...)` 的第一次遍历
- 用 `total_files_scanned` 动态统计已扫描的文件数
- 进度计算改为动态估算（假设媒体文件占比约 30%）
- 进度条可能不会精确到 50%，但实际扫描完成时会 emit(50, ...)

**替代方案**：如果进度精度很重要，可以先快速统计一次文件总数（用 `os.scandir` 而非 `os.walk`，性能更好），但仍是两次遍历。

---

### 修复 5：video_metadata 添加内存缓存

**方案**：用 `functools.lru_cache` 或自定义字典缓存视频元数据。

**改动**：

```python
# api_server.py 顶部
from functools import lru_cache

# 视频元数据缓存（最多缓存 500 个视频）
@lru_cache(maxsize=500)
def _cached_video_metadata(file_path_str: str, file_mtime: float) -> dict:
    """缓存视频元数据，key 为 (路径, mtime)
    
    mtime 变化时缓存失效（用户可能替换了文件）
    """
    try:
        from .video_processor import VideoProcessor
    except ImportError:
        from video_processor import VideoProcessor
    
    return VideoProcessor.extract_metadata(file_path_str) or {}

@app.route('/api/video/metadata', methods=['GET'])
def video_metadata():
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'error': '缺少 path 参数'}), 400
        
        path = urllib.parse.unquote(path)
        file_path = Path(path)
        
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'error': f'文件不存在: {path}'}), 404
        
        # 安全检查
        album_path = get_album_path()
        if album_path:
            try:
                file_path.resolve().relative_to(Path(album_path).resolve())
            except ValueError:
                return jsonify({'error': '访问被拒绝：文件不在相册目录内'}), 403
        
        # 获取文件 mtime 作为缓存 key 的一部分
        file_mtime = file_path.stat().st_mtime
        
        # 调用缓存的元数据提取
        metadata = _cached_video_metadata(str(file_path), file_mtime)
        
        if not metadata:
            return jsonify({
                'available': False,
                'message': 'FFmpeg 不可用或无法提取元数据'
            })
        
        # ... 后续格式化代码不变 ...
```

**关键细节**：
- 缓存 key 包含 `(file_path, file_mtime)`，文件修改后缓存自动失效
- `maxsize=500` 限制缓存大小，防止内存泄漏
- `lru_cache` 自动淘汰最久未使用的缓存

**风险**：
- `lru_cache` 不是线程安全的，但 Flask 的 WSGI 服务器通常是单线程处理请求
- 如果需要多进程部署，需要改用 Redis 或文件缓存

**替代方案**：如果 `lru_cache` 不适用，可以用字典 + 手动清理：

```python
_video_metadata_cache = {}
_video_metadata_lock = threading.Lock()

def _get_cached_metadata(file_path: str, file_mtime: float) -> dict:
    cache_key = f"{file_path}:{file_mtime}"
    with _video_metadata_lock:
        if cache_key in _video_metadata_cache:
            return _video_metadata_cache[cache_key]
    
    # 缓存未命中，调用 FFmpeg
    metadata = VideoProcessor.extract_metadata(file_path) or {}
    
    with _video_metadata_lock:
        # 限制缓存大小
        if len(_video_metadata_cache) > 500:
            # 删除最旧的条目
            oldest_key = next(iter(_video_metadata_cache))
            del _video_metadata_cache[oldest_key]
        _video_metadata_cache[cache_key] = metadata
    
    return metadata
```

---

### 修复 6：App.tsx 状态分离

**方案**：将不相关的状态分离到独立的 Context 或 Zustand store。

**方案选择**：

| 方案 | 优点 | 缺点 |
|---|---|---|
| React Context | 原生支持，无需额外依赖 | 需要手动优化，否则性能更差 |
| Zustand | 轻量、自动优化（selector） | 引入新依赖 |
| 组件内部状态 | 无需改动架构 | 需要大幅重构 |

**推荐**：Zustand，原因：
- 轻量（~1KB）
- 自动优化：只有使用到该状态的组件才会重渲染
- 无需 Provider 包裹，使用简单

**改动概要**：

```tsx
// stores/appStore.ts
import { create } from 'zustand';

interface AppState {
  // 全局状态
  initialized: boolean;
  isFirstRun: boolean;
  currentView: 'timeline' | 'favorites' | 'albums' | 'album-detail' | 'folder';
  
  // 相册路径相关
  albumPath: string | null;
  stats: { total: number; videos: number; size: string } | null;
  
  // 照片列表相关（独立，翻页时不影响其他组件）
  photos: Photo[];
  loading: boolean;
  totalPhotos: number;
  currentPage: number;
  hasMore: boolean;
  
  // 选择模式相关（独立，选择时不影响其他组件）
  selectionMode: boolean;
  selectedIds: Set<string>;
  
  // Actions
  setInitialized: (value: boolean) => void;
  setCurrentView: (view: AppState['currentView']) => void;
  setPhotos: (photos: Photo[]) => void;
  setLoading: (loading: boolean) => void;
  // ... 其他 actions
}

export const useAppStore = create<AppState>((set) => ({
  initialized: false,
  isFirstRun: false,
  currentView: 'timeline',
  albumPath: null,
  stats: null,
  photos: [],
  loading: true,
  totalPhotos: 0,
  currentPage: 1,
  hasMore: false,
  selectionMode: false,
  selectedIds: new Set(),
  
  setInitialized: (value) => set({ initialized: value }),
  setCurrentView: (view) => set({ currentView: view }),
  setPhotos: (photos) => set({ photos }),
  setLoading: (loading) => set({ loading }),
  // ... 其他 actions
}));

// App.tsx
import { useAppStore } from './stores/appStore';

function AppContent() {
  const { t } = useI18n();
  const initialized = useAppStore((state) => state.initialized);
  const currentView = useAppStore((state) => state.currentView);
  
  // 只有 initialized 或 currentView 变化时，AppContent 才会重渲染
  
  return (
    <div>
      <Header />
      <Sidebar />
      <MainContent />
    </div>
  );
}

// Sidebar.tsx
function Sidebar() {
  const stats = useAppStore((state) => state.stats);
  // 只有 stats 变化时，Sidebar 才会重渲染
  // ...
}

// MainContent.tsx
function MainContent() {
  const photos = useAppStore((state) => state.photos);
  const loading = useAppStore((state) => state.loading);
  // 只有 photos 或 loading 变化时，MainContent 才会重渲染
  // ...
}
```

**关键细节**：
- 使用 selector（`useAppStore((state) => state.photos)`）确保只有使用到该状态的组件才会重渲染
- 将相关状态分组（如 `photos`、`loading`、`currentPage` 属于照片列表模块）
- Actions 用 `set` 更新状态，Zustand 自动触发相关组件重渲染

**风险**：
- 需要重构现有代码，工作量较大
- 需要确保所有组件都正确使用 selector

**替代方案（低风险）**：如果不想引入 Zustand，可以用 React Context + `useMemo` 优化：

```tsx
// contexts/PhotosContext.tsx
const PhotosContext = createContext<{
  photos: Photo[];
  loading: boolean;
  // ...
} | null>(null);

function PhotosProvider({ children }) {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  // ...
  
  const value = useMemo(() => ({ photos, loading, ... }), [photos, loading, ...]);
  
  return (
    <PhotosContext.Provider value={value}>
      {children}
    </PhotosContext.Provider>
  );
}

// 使用
function MainContent() {
  const { photos, loading } = useContext(PhotosContext);
  // ...
}
```

**注意**：Context 方案需要确保 `value` 用 `useMemo` 包裹，否则每次 Provider 重渲染都会导致所有 Consumer 重渲染。

---

## 实施顺序

| 步骤 | 任务 | 预估时间 | 风险 |
|------|------|----------|------|
| 1 | 导入检查合并为单次遍历 | 30 分钟 | 低 — 进度精度略有损失 |
| 2 | video_metadata 添加缓存 | 30 分钟 | 低 — 需验证 lru_cache 线程安全性 |
| 3 | App.tsx 状态分离 | 2-3 小时 | 中 — 需要重构现有代码 |

**建议**：步骤 1 和 2 可以先做，风险低收益明显。步骤 3 改动大，可以在 P0 完成后再做。

---

## 各修复项测试与验收

### 修复 4：导入检查合并为单次遍历

#### 测试

1. **功能测试 — 基本导入检查**：
   - 选择一个包含 100+ 照片的源目录
   - 点击「检查导入路径」
   - 确认进度条正常推进（0% → 50% → 100%）
   - 确认最终结果显示正确的文件数量、大小

2. **功能测试 — 源重复检测**：
   - 选择一个包含重复照片的源目录
   - 确认源重复检测结果正确
   - 确认重复组显示正确

3. **功能测试 — 目标重复检测**：
   - 选择一个与相册有重复照片的源目录
   - 确认目标重复检测结果正确
   - 确认重复照片显示正确

4. **功能测试 — 大目录**：
   - 选择一个包含 5000+ 文件的源目录
   - 记录导入检查耗时
   - 预期：耗时比修复前减少 30-50%

5. **进度精度验证**：
   - 观察进度条推进是否平滑
   - 确认进度不会出现「卡住」或「跳跃」
   - 确认最终进度准确到达 100%

6. **日志验证**：
   - 查看后端日志
   - 确认只有一次「开始扫描源目录」日志
   - 确认没有两次 `os.walk` 的日志

#### 验收标准

- [ ] 导入检查功能正常，进度条平滑推进
- [ ] 源重复检测结果正确
- [ ] 目标重复检测结果正确
- [ ] 大目录（5000+ 文件）导入检查耗时减少 30%+
- [ ] 后端日志显示只有一次目录遍历
- [ ] 最终结果与修复前一致

---

### 修复 5：video_metadata 添加缓存

#### 测试

1. **功能测试 — 基本视频元数据**：
   - 选择一个包含视频的目录
   - 点击视频打开详情面板
   - 确认视频元数据（时长、分辨率、编码）正确显示

2. **功能测试 — 缓存命中**：
   - 第一次打开视频详情，记录响应时间（通过浏览器 Network 面板）
   - 关闭详情，再次打开同一视频的详情
   - 预期：第二次响应时间 < 10ms（缓存命中）
   - 对比第一次响应时间（约 100-500ms）

3. **功能测试 — 缓存失效**：
   - 打开视频详情，确认元数据显示
   - 手动修改视频文件（或替换为另一个视频）
   - 再次打开详情
   - 预期：显示新的元数据（缓存因 mtime 变化而失效）

4. **功能测试 — 多视频**：
   - 浏览包含 10+ 视频的目录
   - 依次打开每个视频的详情
   - 确认所有视频元数据正确显示
   - 确认没有缓存错乱（A 视频的元数据显示在 B 视频上）

5. **内存泄漏验证**：
   - 连续打开 100+ 不同视频的详情
   - 观察应用内存占用
   - 预期：内存增长平稳，不会无限增长（lru_cache 限制 500 条）

6. **并发测试**：
   - 同时打开多个视频详情（如果支持）
   - 确认没有线程安全问题
   - 确认缓存正常工作

#### 验收标准

- [ ] 视频元数据正确显示（时长、分辨率、编码）
- [ ] 同一视频第二次打开详情，响应时间 < 10ms
- [ ] 视频文件修改后，缓存自动失效，显示新元数据
- [ ] 多视频浏览时，缓存无错乱
- [ ] 连续打开 100+ 视频后，内存增长平稳
- [ ] 后端无报错日志

---

### 修复 6：App.tsx 状态分离

#### 测试

1. **功能测试 — 首页加载**：
   - 启动应用
   - 确认首页正常加载（统计、目录树、照片列表）
   - 确认没有功能缺失

2. **功能测试 — 翻页**：
   - 浏览照片列表，翻页
   - 确认翻页正常
   - 确认 Sidebar、Header 没有不必要的重渲染

3. **功能测试 — 选择模式**：
   - 进入选择模式，选中多张照片
   - 确认选择功能正常
   - 确认 TimelineView（如果在其他标签页）没有重渲染

4. **功能测试 — 视图切换**：
   - 切换不同视图（时间线、收藏、相册）
   - 确认视图切换正常
   - 确认状态保持正确

5. **功能测试 — 导入流程**：
   - 执行完整的导入流程
   - 确认导入进度、结果正常显示
   - 确认导入完成后状态正确更新

6. **性能验证**：
   - 打开 React DevTools Profiler
   - 录制翻页操作
   - 检查 Sidebar、Header 组件的渲染次数
   - 预期：翻页时 Sidebar、Header 不重渲染

7. **回归测试**：
   - 确认所有核心功能正常：
     - 照片浏览、预览
     - 收藏功能
     - 相册管理
     - 导入功能
     - 设置修改
     - 主题切换
     - 语言切换

#### 验收标准

- [ ] 首页加载正常，无功能缺失
- [ ] 翻页功能正常
- [ ] 选择模式功能正常
- [ ] 视图切换正常，状态保持正确
- [ ] 导入流程正常
- [ ] React DevTools Profiler 显示：翻页时 Sidebar、Header 不重渲染
- [ ] 所有核心功能回归测试通过
- [ ] 前端构建无报错

---

## 整体验收标准

- [ ] 所有修复项的单独验收标准均通过
- [ ] 应用启动正常，无控制台报错
- [ ] 后端无异常日志
- [ ] 性能指标提升：
  - 导入检查耗时减少 30%+
  - 视频元数据二次打开响应 < 10ms
  - 翻页时不相关组件不重渲染
- [ ] 所有核心功能正常：
  - 照片浏览、导入、删除
  - 视频播放、元数据显示
  - 相册管理
  - 收藏功能
  - 设置修改
- [ ] 移动端访问正常（如有影响）
