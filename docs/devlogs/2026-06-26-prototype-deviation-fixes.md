# PhotoPreview 原型偏差修复 实施计划

**对应审计报告**：[2026-06-26-photo-preview-audit.md](./2026-06-26-photo-preview-audit.md)
**创建日期**：2026-06-26
**预计工时**：~8 小时 / 1 人天
**目标**：让 PhotoPreview.tsx 像素级对齐 [photo-preview-v2.html](../../docs/prototypes/desktop/photo-preview-v2.html) 原型 + 功能完整覆盖 spec §12.3

---

## 总体策略

| 阶段 | 范围 | 工时 | 必须性 |
|------|------|------|--------|
| **Phase 1 - P0 功能修复** | F1/F2/F3/F4/F5/F9 + D1 | 3h | **必修** |
| **Phase 2 - P0 视觉修复** | 视觉 #1-#6 | 1h | **必修** |
| **Phase 3 - P1 视觉 + 数据流** | 视觉 #7-#28 + D2-D4/D6 | 3h | 应修 |
| **Phase 4 - P2 细节** | 视觉 #29-#42 + D5/D7/D8 | 1h | 可选 |
| **Phase 5 - 验收测试** | 跑测试 + 手动验证 | 1h | **必修** |

---

## Phase 1：P0 功能修复（必修）

### 1.1 添加 ✕ 关闭按钮（F1）

**文件**：[PhotoPreview.tsx](../../frontend/src/components/dialogs/PhotoPreview.tsx#L232-L240)

**当前**：❤ 收藏 | 分隔线 | ⓘ 信息面板 | ▶ 幻灯片（无 onClick）

**修改**：在 ▶ 幻灯片之后加 ✕ 关闭按钮

```tsx
{/* ✕ 关闭按钮 */}
<button
  onClick={onClose}
  className="w-9 h-9 inline-flex items-center justify-center rounded-md text-text-secondary hover:bg-page hover:text-text-primary transition-all duration-150"
  title={`${t('common.close')} (Esc)`}
>
  <svg className="w-[18px] h-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M18 6L6 18M6 6l12 12" />
  </svg>
</button>
```

**验收**：点击 ✕ 触发 onClose，按 Esc 等价。

---

### 1.2 实现 ▶ 幻灯片播放（F2）

**位置**：[PhotoPreview.tsx](../../frontend/src/components/dialogs/PhotoPreview.tsx) line 1-50（state + useEffect）

**新增 state**：
```tsx
const [isSlideshow, setIsSlideshow] = useState(false);
```

**新增 useEffect**（在现有 useEffect 之后）：
```tsx
useEffect(() => {
  if (!isSlideshow || photos.length === 0) return;
  const timer = setInterval(() => {
    setCurrentIndex((i) => (i + 1) % photos.length);
  }, 3000);
  return () => clearInterval(timer);
}, [isSlideshow, photos.length]);
```

**绑定按钮**：
```tsx
<button
  onClick={() => setIsSlideshow((s) => !s)}
  className={`w-9 h-9 inline-flex items-center justify-center rounded-md transition-all duration-150 ${
    isSlideshow ? 'text-primary bg-primary-light' : 'text-text-secondary hover:bg-page hover:text-text-primary'
  }`}
  title={t('preview.slideShow')}
>
  {isSlideshow ? (
    // pause icon
  ) : (
    // play icon
  )}
</button>
```

**Esc 退出**：在键盘快捷键 useEffect 中加 `if (e.key === 'Escape' && isSlideshow) { setIsSlideshow(false); return; }`

**验收**：
- 点击 ▶ 进入幻灯片，每 3 秒跳下一张
- 到底后循环到第 1 张
- 按 Esc 退出幻灯片（但不关闭预览）
- 再点按钮（变为暂停图标）也退出

---

### 1.3 翻页环形跳转（F3）

**位置**：[PhotoPreview.tsx](../../frontend/src/components/dialogs/PhotoPreview.tsx#L249-L270)

**当前**：
```tsx
{currentIndex > 0 && <button onClick={handlePrev}>←</button>}
{currentIndex < photos.length - 1 && <button onClick={handleNext}>→</button>}
```

**修改**：
```tsx
<button
  onClick={handlePrev}
  disabled={photos.length <= 1}
  className="absolute left-9 top-1/2 -translate-y-1/2 w-11 h-11 bg-card border border-border rounded-full flex items-center justify-center text-text-secondary hover:text-primary hover:border-primary hover:scale-105 active:scale-95 transition-all duration-150 z-10 shadow-md"
  title={`${t('preview.prev')} (←)`}
>
  <svg ...>←</svg>
</button>
<button
  onClick={handleNext}
  disabled={photos.length <= 1}
  className="absolute right-9 top-1/2 -translate-y-1/2 w-11 h-11 ... shadow-md"
  title={`${t('preview.next')} (→)`}
>
  <svg ...>→</svg>
</button>
```

**修改 handler**：
```tsx
const handlePrev = useCallback(() => {
  setCurrentIndex((i) => (i - 1 + photos.length) % photos.length);
}, [photos.length]);

const handleNext = useCallback(() => {
  setCurrentIndex((i) => (i + 1) % photos.length);
}, [photos.length]);
```

**注意**：
- `left-9` = 36px（对齐原型）
- `hover:scale-105`（不是 110，保留 `translateY(-50%)`）
- `shadow-md` 加 box-shadow

**验收**：第 1 张时点 ← 跳到最后 1 张；最后 1 张时点 → 跳到第 1 张。

---

### 1.4 视频离开时暂停（F4）+ 切下一张释放（F5）

**位置**：[PhotoPreview.tsx](../../frontend/src/components/dialogs/PhotoPreview.tsx) line 56-60

**当前**：
```tsx
useEffect(() => {
  if (photo?.type === 'video' && videoRef.current) {
    videoRef.current.play().catch(() => {});
  }
}, [photo]);
```

**修改为**：
```tsx
useEffect(() => {
  if (!photo) return;
  const video = videoRef.current;
  if (photo.type === 'video' && video) {
    // 切下一张时先释放旧 src
    if (video.src) {
      video.pause();
      video.removeAttribute('src');
      video.load();
    }
    // 设置新 src 并自动播放
    video.src = api.getFile(photo.path);
    video.load();
    video.play().catch(() => {});
  }
  // cleanup：离开预览页时暂停
  return () => {
    if (video) {
      video.pause();
      video.removeAttribute('src');
      video.load();
    }
  };
}, [photo]);
```

**验收**：
- 快速翻页不卡顿
- 关闭预览后视频不继续播放
- DevTools Memory 不会持续上涨

---

### 1.5 PhotoPreviewProps.onPhotoUpdate（F9）

**位置**：[PhotoPreview.tsx](../../frontend/src/components/dialogs/PhotoPreview.tsx) line 9-15（接口定义）

**新增 prop**：
```tsx
interface PhotoPreviewProps {
  photo: Photo;
  photos: Photo[];
  onClose: () => void;
  // v0.7 新增
  onPhotoUpdate?: (updated: Photo) => void;  // ← 新增
}
```

**App.tsx 改造**（[App.tsx](../../frontend/src/App.tsx) line 380-410）：
```tsx
<PhotoPreview
  photo={previewPhoto}
  photos={state.photos}
  onClose={() => setPreviewPhoto(null)}
  onPhotoUpdate={(updated) => {
    setState((prev) => ({
      ...prev,
      photos: prev.photos.map((p) => (p.id === updated.id ? updated : p)),
    }));
  }}
/>
```

**在 PhotoPreview.tsx 的 title/description 保存处**：
```tsx
onBlur={async () => {
  try {
    const updated = { ...photo, title: titleText };
    await api.updatePhotoTitle(photo.path, titleText);
    onPhotoUpdate?.(updated);
    setTitleState('saved');
    setTimeout(() => setTitleState('default'), 1500);
  } catch (err) {
    setTitleState('error');
    showToast('保存失败', 'error');
  }
}}
```

**验收**：在预览中改 title，关闭预览后再点击同张照片，title 保持新值（不再回退）。

---

## Phase 2：P0 视觉修复（必修）

### 2.1 主图尺寸 + aspect-ratio（视觉 #2 #3）

**位置**：[PhotoPreview.tsx](../../frontend/src/components/dialogs/PhotoPreview.tsx) line 280-289

**当前**：
```tsx
<img className="max-w-full max-h-full object-contain rounded-md shadow-lg bg-black" />
```

**修改**：
```tsx
<img
  src={api.getFile(photo.path)}
  alt={photo.name}
  className="max-w-full max-h-full object-contain rounded-md shadow-lg"
  style={{
    width: '800px',
    maxWidth: '100%',
    aspectRatio: '3 / 2',
    background: 'linear-gradient(135deg, #ff8a5b 0%, #c156e6 50%, #5b8def 100%)',
  }}
/>
```

**视频同样处理**（main-video）：
```tsx
<video
  ...
  style={{
    width: '800px',
    maxWidth: '100%',
    aspectRatio: '3 / 2',
    background: '#000',
  }}
  className="max-w-full max-h-full object-contain rounded-md shadow-lg"
/>
```

**验收**：主图有 3:2 比例，占位显示橙色→紫色→蓝色渐变（不是黑色）。

---

### 2.2 翻页按钮位置 + 缩放 + shadow（视觉 #4 #5 #6）

见 Phase 1.3，hover:scale-105 + shadow-md + left-9/right-9。

---

## Phase 3：P1 视觉 + 数据流（应修）

### 3.1 P1 视觉 22 项

**位置**：[PhotoPreview.tsx](../../frontend/src/components/dialogs/PhotoPreview.tsx) 全文 + [index.css](../../frontend/src/index.css)

**修改方式**（举几个关键项）：

| 项 | 改动 |
|---|------|
| 顶栏 z-index | 加 `z-10` 或 `zIndex: 10` |
| file-sub 分隔符 | `<span className="opacity-40 mx-1.5">·</span>`（mx-1.5 = 6px）|
| type-badge 圆角 | 改 `rounded-[12px]` 替换 `rounded-full` |
| divider-v 高度 | `h-[22px]` 替换 `h-5` |
| 主区 overflow | 加 `overflow-hidden` |
| 缩略图条 padding | `px-5`（20px）替换 `px-4` |
| 缩略图条 gap | `gap-1.5`（6px）替换 `gap-1` |
| 缩略图 active | 改用 `border-2 border-primary` + `shadow-[0_0_0_3px_rgba(8,145,178,0.08)]` |
| panel padding | 拆出 `panel-section` 组件，`p-5` 改 `px-[22px] py-5` |
| panel-section 分隔 | 加 `border-b border-border`，最后一个用 `last:border-b-0` |
| panel-label | `text-[11px]` + `tracking-[0.6px]` |
| title | `text-[22px] font-bold`（替换 text-xl）|
| desc | 加 `leading-[1.65]`，`min-h-[48px]` 替换 `min-h-[60px]` |
| meta-row | 加 `mb-2.5`（10px）|
| meta-icon | `w-3.5 h-3.5`（14px）|
| meta-chip | `rounded-[12px] px-[9px] text-[12px] gap-[5px]` |

**缩略图条滚动条样式**（[index.css](../../frontend/src/index.css) 新增）：
```css
.thumbs-bar::-webkit-scrollbar { height: 6px; }
.thumbs-bar::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: 3px; }
```

**info-panel 滚动条**（同 index.css）：
```css
.info-panel::-webkit-scrollbar { width: 6px; }
.info-panel::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: 3px; }
```

---

### 3.2 P1 数据流 4 项

**D2 - 错误处理**：4 处 API 调用加 try/catch
```tsx
const handleFavoriteToggle = useCallback(async () => {
  try {
    if (isFavorite) {
      await api.removeFavorite(photo.path);
    } else {
      await api.addFavorite(photo.path);
    }
    setIsFavorite(!isFavorite);
  } catch (err) {
    showToast(t('preview.favoriteFailed') || '操作失败', 'error');
  }
}, [isFavorite, photo.path, showToast]);
```

**D3 - loading 态**：getPhotoAlbums 加 loading state
```tsx
const [loadingAlbums, setLoadingAlbums] = useState(false);
useEffect(() => {
  let cancelled = false;
  const load = async () => {
    setLoadingAlbums(true);
    try {
      const res = await api.getPhotoAlbums(photo.path);
      if (!cancelled) setPhotoAlbums(res.albums);
    } catch (err) {
      if (!cancelled) showToast('加载相册失败', 'error');
    } finally {
      if (!cancelled) setLoadingAlbums(false);
    }
  };
  load();
  return () => { cancelled = true; };
}, [photo.path]);
```

**D4 - toast 反馈**：title/description/albums 成功保存后 showToast（success）
**D6 - 父组件同步**：见 Phase 1.5

---

## Phase 4：P2 细节（可选）

### 4.1 14 项 P2 视觉

| 项 | 改动 |
|---|------|
| meta-chip svg 不统一 | 全部改 `w-3 h-3`（12px）|
| album-link gap | `gap-3`（12px）|
| album-link 静态 bg | `bg-page` |
| album-link 缩略图 | `w-12 h-12`（48px）|
| album-link chevron | `w-3.5 h-3.5`（14px）|
| 缩略图渐变 fallback | `background: 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)'` |
| font-family 字体栈 | 在 body 改字体栈为 spec §12.3.6 |
| type-badge svg gap | `gap-1`（4px）|
| ... | 其他 6 项类似 |

### 4.2 3 项 P2 数据流

**D5 - 防抖**：title/description 用 useDebounce hook
```tsx
import { useDebouncedCallback } from 'use-debounce';
const debouncedSaveTitle = useDebouncedCallback(async (value) => {
  await api.updatePhotoTitle(photo.path, value);
}, 500);
```

**D7 - 收藏状态同步**：photos 变化时同步 isFavorite state
```tsx
useEffect(() => {
  setIsFavorite(photo.is_favorite || false);
}, [photo.id, photo.is_favorite]);
```

**D8 - 资源竞争**：快速翻页时 abort 上一个 fetch
```tsx
useEffect(() => {
  const controller = new AbortController();
  // 加载相册时传 signal
  return () => controller.abort();
}, [photo.path]);
```

---

## Phase 5：验收测试（必修）

### 5.1 自动化测试

```bash
cd frontend
npm run build       # 必须 0 error
npx tsc --noEmit    # 类型检查
npm run lint        # 如果有 ESLint 配置
```

```bash
cd ..
pytest              # 后端 746 tests 仍然全过
```

### 5.2 手动验收清单

打开 PhotoPreview 逐项验证：

**P0 功能**：
- [ ] ✕ 关闭按钮存在且可用
- [ ] ▶ 幻灯片按钮可点击，每 3 秒跳下一张，Esc 退出
- [ ] 第 1 张时 ← 仍可见，点击跳到最后
- [ ] 最后 1 张时 → 仍可见，点击跳到第 1 张
- [ ] 视频切换时不卡顿、不后台播放
- [ ] 改 title/desc 后关闭再打开，新值保留

**P0 视觉**：
- [ ] 主图有 3:2 比例，宽度限制 800px
- [ ] 主图占位是橙→紫→蓝渐变
- [ ] 翻页按钮距离边缘 36px
- [ ] 翻页按钮 hover 时不脱离垂直居中
- [ ] 翻页按钮有阴影

**P1 视觉**：
- [ ] panel-section 之间有分隔线
- [ ] title 是 22px
- [ ] panel-label 是 11px 大写
- [ ] 缩略图条缩略图间距是 6px
- [ ] 缩略图 active 是 primary 边框 + 光晕（不是 ring）
- [ ] type-badge 是圆角矩形不是 pill

**P1 数据流**：
- [ ] 收藏失败有 toast
- [ ] 加载相册中显示 loading
- [ ] 改 title 成功后有成功提示

### 5.3 视觉对比截图

用浏览器 MCP 截图，跟 [photo-preview-v2.html](../../docs/prototypes/desktop/photo-preview-v2.html) 截图逐项对比。

---

## 实施顺序建议

| 顺序 | Phase | 估计时间 | 提交粒度 |
|------|-------|---------|---------|
| 1 | Phase 1.1（✕ 关闭按钮）| 15min | 1 commit |
| 2 | Phase 1.2（幻灯片）| 45min | 1 commit |
| 3 | Phase 1.3（环形翻页）| 30min | 1 commit |
| 4 | Phase 1.4 + 1.5（视频清理 + 父组件同步）| 45min | 1 commit |
| 5 | Phase 2（视觉 P0）| 1h | 1 commit |
| 6 | Phase 3.1（P1 视觉 22 项）| 1.5h | 1 commit |
| 7 | Phase 3.2（P1 数据流 4 项）| 1.5h | 1 commit |
| 8 | Phase 4（P2 细节）| 1h | 1 commit |
| 9 | Phase 5（验收测试）| 1h | — |

**总计**：~8h

---

## 风险与依赖

### 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Phase 1.5 onPhotoUpdate 改动影响 App.tsx 状态管理 | 中 | 中 | 提交前单独跑 pytest 验证 |
| 视频 src 释放逻辑可能在某些浏览器不兼容 | 低 | 中 | 测 Chrome/Edge/Firefox 三个浏览器 |
| Tailwind JIT 编译 `rounded-[12px]` 等任意值可能需要转义 | 低 | 低 | 用方括号语法 `rounded-[12px]` 即可 |

### 依赖

- **后端**：[api_server.py](../../backend/api_server.py) 需有 `getPhotoAlbums` / `updatePhotoTitle` / `updatePhotoDescription` / `addFavorite` / `removeFavorite` 接口
  - 已确认：getPhotoAlbums 存在，其他待审计时确认
- **类型**：[types/index.ts](../../frontend/src/types/index.ts) 需添加 `width/height` 字段到 Photo 接口

---

## 后续行动

- [ ] Phase 1.1 修复 ✕ 按钮
- [ ] Phase 1.2 实现幻灯片
- [ ] Phase 1.3 环形翻页
- [ ] Phase 1.4 视频资源清理
- [ ] Phase 1.5 onPhotoUpdate 同步
- [ ] Phase 2 P0 视觉
- [ ] Phase 3.1 P1 视觉 22 项
- [ ] Phase 3.2 P1 数据流 4 项
- [ ] Phase 4 P2 细节
- [ ] Phase 5 验收测试 + 截图对比
