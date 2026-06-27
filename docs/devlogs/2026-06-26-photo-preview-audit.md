# PhotoPreview.tsx 审计报告

**审计日期**：2026-06-26
**审计范围**：[PhotoPreview.tsx](../../frontend/src/components/dialogs/PhotoPreview.tsx)（v0.7 重构后）
**比对基准**：
- [docs/prototypes/desktop/photo-preview-v2.html](../../docs/prototypes/desktop/photo-preview-v2.html)
- [docs/superpowers/specs/2026-06-24-v0.7-album-ui-spec.md](../superpowers/specs/2026-06-24-v0.7-album-ui-spec.md) §12.3

**审计方法**：逐行对照原型 CSS 与 spec 功能规格，按"视觉对齐 / 功能完整 / 数据流"三类记录偏差。

---

## 总览

| 类别 | 偏差数 | 严重 |
|------|--------|------|
| 视觉对齐（CSS 偏差） | 42 | P1 |
| 功能完整（缺失行为） | 11 | **P0** |
| 数据流（错误处理 / 状态机） | 8 | P1-P2 |
| **合计** | **61** | — |

---

## 1. 视觉对齐（42 项，按 P0/P1/P2 分级）

### P0：直接破坏交互/可发现性（6 项）

| # | 位置 | 原型/规格 | 当前实现 | 影响 |
|---|------|----------|---------|------|
| 1 | 顶栏按钮区 | spec §12.3.2 4 按钮 `❤ ⓘ ▶ ✕` | **完全缺 ✕** | 用户无法从顶栏关闭预览 |
| 2 | 主图容器 | 原型 `width: 800px; aspect-ratio: 3/2` | `max-w-full max-h-full` 无尺寸约束 | 照片 1:1 显示，破坏长宽比 |
| 3 | 主图背景 | 原型 `linear-gradient(135deg, #ff8a5b 0%, #c156e6 50%, #5b8def 100%)` | `bg-black` | 占位图是纯黑，跟"无图"看起来一样 |
| 4 | 翻页按钮位置 | 原型 `left: 36px; right: 36px` | `left-4 right-4` = 16px | 翻页按钮过于贴边 |
| 5 | 翻页 hover | 原型 `transform: translateY(-50%) scale(1.05)` | `hover:scale-110`（无 translateY 保护） | hover 时按钮脱离垂直居中 |
| 6 | 翻页 box-shadow | 原型 `box-shadow: var(--shadow-md)` | 缺 | 按钮没有浮起感 |

### P1：可观察的视觉偏差（22 项）

| # | 位置 | 原型 | 当前 | 差值 |
|---|------|------|------|------|
| 7 | 顶栏 z-index | `z-index: 10` | 无 | — |
| 8 | file-sub 分隔符 | `margin: 0 6px; opacity: 0.4` | 无 margin | 视觉拥挤 |
| 9 | type-badge 圆角 | `border-radius: 12px` | `rounded-full` = 9999px | 形状不符（pill vs 胶囊） |
| 10 | divider-v 高度 | `height: 22px` | `h-5` = 20px | -2px |
| 11 | 主区 overflow | `overflow: hidden` | 缺 | 视频可能溢出 |
| 12 | 缩略图条 padding | `padding: 0 20px` | `px-4` = 16px | -4px |
| 13 | 缩略图条 gap | `gap: 6px` | `gap-1` = 4px | -2px |
| 14 | 缩略图条滚动条 | `::-webkit-scrollbar { height: 6px }` | 用全局样式 | 颜色不匹配 |
| 15 | 缩略图 hover | `transform: translateY(-2px)` | `hover:scale-105` | 动作不符 |
| 16 | 缩略图 active | `border-color: primary + box-shadow 0 0 0 3px primary-light` | `ring-2 ring-primary ring-offset-2` | Tailwind ring 不等价于 border+box-shadow |
| 17 | 缩略图视频图标 | `top: 6px right: 6px 18×18` | `top-1 right-1 w-4 h-4` = 4px + 16px | 位置/尺寸都不对 |
| 18 | panel padding | `padding: 20px 22px` | `p-5` = 20px 四周 | 水平少 2px |
| 19 | panel-section 分隔 | `border-bottom: 1px solid var(--border)` | 缺 | 区块无视觉分隔 |
| 20 | panel-label 字号 | `font-size: 11px` | `text-xs` = 12px | +1px |
| 21 | panel-label letter-spacing | `letter-spacing: 0.6px` | `tracking-wide` = 0.025em ≈ 0.35px | 差 0.25px |
| 22 | title 字号 | `font-size: 22px; font-weight: 700` | `text-xl font-bold` = 20px | -2px |
| 23 | desc line-height | `line-height: 1.65` | 缺 | 默认 1.5，行高太紧 |
| 24 | desc min-height | `min-height: 48px` | `min-h-[60px]` | +12px |
| 25 | meta-row margin | `margin-bottom: 10px` | 缺 | 跟下一行太近 |
| 26 | meta-icon 尺寸 | `width: 14px; height: 14px` | `w-4 h-4` = 16px | +2px |
| 27 | meta-chip 圆角 | `border-radius: 12px` | `rounded-full` | pill vs 胶囊 |
| 28 | meta-chip padding | `padding: 0 9px` | `px-2.5` = 10px | +1px |

### P2：细节优化（14 项）

| # | 位置 | 原型 | 当前 | 差值 |
|---|------|------|------|------|
| 29 | meta-chip 字号 | `font-size: 12px` | `text-[11px]` | -1px |
| 30 | meta-chip gap | `gap: 5px` | `gap-1.5` = 6px | +1px |
| 31 | meta-chip svg | `width: 12px; height: 12px` | `w-3 h-3` 部分为 `w-4 h-4` | 不统一 |
| 32 | album-link gap | `gap: 12px` | `gap-2.5` = 10px | -2px |
| 33 | album-link 静态 bg | `background: var(--bg-page)` | 缺 | 跟页面背景混淆 |
| 34 | album-link 缩略图 | `width: 48px; height: 48px` | `w-9 h-9` = 36px | -12px |
| 35 | album-link chevron | `width: 14px; height: 14px` | `w-4 h-4` = 16px | +2px |
| 36 | 缩略图缺渐变 fallback | `background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)` | 缺 | 缩略图加载时显示为白 |
| 37 | 缩略图视频时长 padding | `padding: 1px 5px; border-radius: 3px` | 部分未对齐 | — |
| 38 | panel 滚动条 | `::-webkit-scrollbar { width: 6px; thumb bg border }` | 继承全局 | thumb 颜色可能不一致 |
| 39 | font-family 字体栈 | spec §12.3.6 完整字体栈 | 用全局 var | 待确认值 |
| 40 | type-badge svg gap | `gap: 4px` | 无 | — |
| 41 | type-badge 视频/照片 | `.video { bg: primary-light, color: primary }` `.photo { bg: page, color: text-secondary }` | ✓ 颜色 OK | 顺序略乱 |
| 42 | 关闭按钮 ✕ 缺失 | 见 P0 #1 | — | — |

---

## 2. 功能完整（11 项，**全部 P0**）

| # | 功能 | spec 位置 | 当前状态 | 缺失原因 |
|---|------|----------|---------|---------|
| F1 | **✕ 关闭按钮** | §12.3.2 "4 个按钮" | ❌ 完全缺失 | UI 设计漏项 |
| F2 | **▶ 幻灯片播放** | §12.3.2 "3 秒/张，Esc 退出" | ❌ 按钮无 onClick，状态机完全没写 | 功能未实现 |
| F3 | **翻页环形跳转** | §12.3.7.3 "边界环形：第 1 张←→ 跳到最后" | ❌ 边界时按钮消失 | 误用 `currentIndex > 0` 条件渲染 |
| F4 | **视频离开时暂停** | §12.3.7.2 "离开预览页：自动 video.pause()" | ❌ 缺 cleanup | useEffect 无 return cleanup |
| F5 | **切下一张释放 video src** | §12.3.7.7 "video.src = '' 立即释放" | ❌ 没实现 | 内存占用累积 |
| F6 | **title 5 态状态机** | §6.6.1 "default/typing/saving/saved/error" | ❌ 只有 default + onBlur | 缺 debounce + loading 反馈 |
| F7 | **description 5 态状态机** | §6.6.1 同上 | ❌ 同 F6 | 同上 |
| F8 | **XMP 同步错误反馈** | §13.1 "原图只读 → 仅写 DB，UI 提示" | ❌ 缺错误 toast | 缺 catch 错误处理 |
| F9 | **PhotoPreviewProps.onPhotoUpdate** | §12.3 隐含（改完应通知父组件刷新） | ❌ 没传回调 | App.tsx 中的 state.photos 不会更新 |
| F10 | **API 失败 toast** | 通用需求 | ❌ console.error 无 UI 反馈 | 收藏/相册/标题失败用户看不到 |
| F11 | **photo type 添加 width/height** | spec §12.3.2 "拍摄信息：4 个 chip（3:2 / 4032×3024 / 4.2MB / 视频时长）" | ❌ Photo 类型无 width/height 字段 | `(photo as any).width` 写死 fallback |

### 关键交互缺失影响

- **F1 + F2**：4 个顶栏按钮缺 2 个，最显眼的两个交互（关闭 / 幻灯片）不可用
- **F3**：第 1 张时 `←` 消失，最后一张时 `→` 消失，跟 spec §12.3.7.3 明确要求的"环形"相反
- **F4 + F5**：视频预览资源不释放，长时间预览累积内存
- **F6-F8**：title/description 改名是 v0.7 主推功能，但保存失败用户完全无感知

---

## 3. 数据流（8 项）

| # | 项目 | 严重 | 说明 |
|---|------|------|------|
| D1 | useEffect 缺 cleanup | P0 | video.play() 后无 pause，会后台播放 |
| D2 | 错误处理缺失 | P1 | 收藏/标题/相册/描述共 4 处 API 调用无 try/catch 反馈 |
| D3 | loading 态缺失 | P1 | getPhotoAlbums 加载中无视觉提示 |
| D4 | toast 反馈缺失 | P1 | 用户操作无成功/失败提示 |
| D5 | 防抖缺失 | P2 | title/description onBlur 即时保存，无 debounce，连续输入可能丢保存 |
| D6 | 父组件状态不同步 | P1 | 改完 title/description 后 App.tsx state.photos 不刷新，关闭预览后再开又变回原值 |
| D7 | 收藏图标 active 状态依赖 | P2 | 依赖 isFavorite prop，但 photos 列表变化时可能 stale |
| D8 | 资源竞争 | P2 | 快速翻页时 videoRef 切换 + play 可能冲突 |

---

## 4. 审计结论

**根本原因**：v0.7 重构 PhotoPreview 时，主要关注"布局重构 + 按钮存在"，但**没建立"原型 → Tailwind 类"映射表**。每个细节都靠肉眼对比，导致 1-2px 级别的偏差大量累积。

**对比之前"按 spec 和原型做的"声明**：

> 用户原话："明明是按 spec 和原型做的"

实际情况是：布局结构（grid 3 行 / 面板 340px / 缩略图 80px）**对齐了**；但**按钮数量缺 2 个、视觉细节 42 项偏差、状态机/错误处理 19 项缺失**。

**修复优先级建议**（见配套实施计划 [2026-06-26-prototype-deviation-fixes.md](./2026-06-26-prototype-deviation-fixes.md)）：

1. **P0 功能修复**（F1/F2/F3/F4/F5/F9/D1）：~15 个文件改动，~3 小时
2. **P0 视觉修复**（#1-#6）：~50 行 CSS，~1 小时
3. **P1 视觉 + 数据流**（#7-#28 + D2-D4/D6）：~3 小时
4. **P2 细节**（#29-#42 + D5/D7/D8）：~1 小时

**总估算**：~8 小时 / 1 人天

---

## 附录 A：i18n 翻译验证

对照 [I18nContext.tsx](../../frontend/src/contexts/I18nContext.tsx) 中所有 `preview.*` key：

| 用到的 key | 存在？ |
|----------|------|
| `preview.back` | ✅ |
| `preview.favorite` | ✅ |
| `preview.infoPanel` | ✅ |
| `preview.slideShow` | ✅ |
| `preview.video` | ✅ |
| `preview.photo` | ✅ |
| `preview.photoCount` | ✅ |
| `preview.albums` | ✅ |
| `preview.noAlbums` | ✅ |
| `preview.addTitle` | ✅ |
| `preview.addDesc` | ✅ |
| `preview.unknownDate` | ✅ |
| `preview.prev` | ✅ |
| `preview.next` | ✅ |
| `common.loading` | ✅ |

**结论**：i18n 翻译完整，无缺失 key。

---

## 附录 B：建议建立"原型 CSS → Tailwind 工具类"映射表

未来 v0.8 重构其他组件时（如 AlbumManageModal / PhotoCard），建议先建立此表，避免类似偏差重复出现。

| 原型 CSS | Tailwind 工具类 |
|---------|---------------|
| `width: 34px; height: 34px` | `w-[34px] h-[34px]` |
| `font-size: 11px` | `text-[11px]` |
| `font-size: 22px; font-weight: 700` | `text-[22px] font-bold` |
| `padding: 0 20px` | `px-5` |
| `gap: 6px` | `gap-1.5` |
| `border-radius: 12px` | `rounded-xl` 或 `rounded-[12px]` |
| `box-shadow: 0 4px 12px rgba(0,0,0,0.08)` | `shadow-md` |
| `transition: all 0.15s` | `transition-all duration-150` |
| `aspect-ratio: 3/2` | `aspect-[3/2]` |
| `linear-gradient(135deg, A 0%, B 100%)` | `bg-gradient-to-br from-[A] to-[B]` |
