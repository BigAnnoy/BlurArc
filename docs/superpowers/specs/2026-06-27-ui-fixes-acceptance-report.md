# 2026-06-27 UI 修复验收报告

**验收日期**: 2026-06-27  
**验收人**: AI Agent (并行 3 个 agent)  
**Spec 文档**: `2026-06-27-ui-fixes-design.md`

---

## 执行摘要

**总通过率**: 5/44 (11.4%)

| 问题 | 通过/总数 | 状态 |
|------|-----------|------|
| 问题 1：布局切换网格/瀑布流 | 1/5 | ❌ 未通过 |
| 问题 2：加入相册弹窗对齐 | 0/8 | ❌ 未通过 |
| 问题 3：照片预览动效 | 1/5 | ❌ 未通过 |
| 问题 4：refreshAllCounters | 0/6 | ❌ 未通过 |
| 问题 5：右键菜单通用化 | 0/5 | ❌ 未通过 |
| 问题 6：排序逻辑统一 | 0/7 | ❌ 未通过 |
| 问题 7：相册封面策略 | 3/8 | ❌ 未通过 |

---

## 详细验收结果

### 问题 1：toolbar 布局切换改为网格/瀑布流

**通过**: 1/5

| 验收项 | 状态 | 说明 |
|--------|------|------|
| toolbar 按钮点击切换"网格/瀑布流" | ❌ | 当前切换的是 `displayMode: 'square' \| 'original'`（正方形/原始比例），不是"网格/瀑布流" |
| 网格模式：正方形卡片 | ✓ | PhotoCard.tsx 有 `aspect-square object-cover` |
| 瀑布流模式：按原始比例高度 | ❌ | 无 CSS columns/masonry 实现 |
| tooltip 显示"布局切换（网格）"/"布局切换（瀑布流）" | ❌ | 当前显示"布局切换（正方形）"/"布局切换（原始比例）" |
| 所有视图均可切换 | ✓ | PhotoToolbar 被 TimelineView 和 MainContent 共用 |

**修复建议**:
1. PhotoToolbar.tsx: `displayMode` → `layoutMode`，值改为 `'grid' \| 'masonry'`
2. PhotoGrid.tsx: 实现 CSS columns 瀑布流（`column-width: 200px`）
3. tooltip 文案改为"布局切换（网格）"/"布局切换（瀑布流）"

---

### 问题 2：加入相册弹窗对齐 modal v3

**通过**: 0/8

| 验收项 | 状态 | 说明 |
|--------|------|------|
| 加入相册弹窗宽度 512px（size=lg） | ❌ | 使用 `w-[560px]`，未使用 Modal size prop |
| header/footer 固定，仅相册网格区滚动 | ❌ | 整体滚动，无固定 header/footer |
| 相册网格区最多展示 6 个格子 | ❌ | 无"最多 6 格"逻辑，新建入口在网格外 |
| 无双重 padding | ❌ | Modal 有 `p-4`，JoinAlbumModal 有 `px-5 pt-4 pb-3` |
| 相册卡片横向布局（cover 48x48 左 + info 右） | ❌ | 使用 `flex flex-col`（纵向布局） |
| 新建相册入口在网格内最后一格 | ❌ | 独立的横向条目，不在网格内 |
| close 按钮圆形，icon × | ❌ | 方形按钮 + ✕ 字符 |
| 其他 Modal 弹窗不受破坏 | ⚠️ | 无法完全验证 |

**修复建议**:
1. 使用 Modal `size="lg"`，去掉 `w-[560px]`
2. 重构为 header/footer 固定 + 中间滚动区域
3. 相册卡片改为横向布局
4. 新建相册入口移入网格最后一格
5. 消除双重 padding

---

### 问题 3：照片预览加完整动效

**通过**: 1/5

| 验收项 | 状态 | 说明 |
|--------|------|------|
| 打开预览：背景淡入 + 主图缩放淡入 | ❌ | `if (!photo || !isOpen) return null` 硬切换 |
| 关闭预览：淡出后卸载 | ❌ | 直接卸载，无淡出过渡 |
| 信息面板开合：平滑过渡 | ❌ | 条件渲染硬切，无 transition |
| 切换上一张/下一张：主图淡入过渡 | ❌ | img 无 key 变化触发动画 |
| 无动画库引入 | ✓ | 未引入 framer-motion 等 |

**修复建议**:
1. 添加背景淡入动画（`animate-fadeIn`）
2. 添加主图缩放淡入（`animate-modal-in`）
3. 关闭时需先淡出再卸载（用 state 控制 opacity transition）
4. 信息面板改用 CSS transition
5. 切换照片时给 img 加 key 触发过渡

---

### 问题 4：计数刷新统一为 refreshAllCounters 函数

**通过**: 0/6

| 验收项 | 状态 | 说明 |
|--------|------|------|
| 加入相册后相册计数立即更新 | ❌ | onJoined 只关闭弹窗，未刷新计数 |
| 拖拽加入相册后计数更新 | ❌ | 拖拽成功后只 showToast |
| 删除照片后所有相关计数更新 | ❌ | handleDeleteComplete 只调用 loadPhotos |
| 扫描新增后文件夹计数更新 | ❌ | handleScanNewFiles 只调用 onSelect |
| 复制相册后相册列表更新 | ❌ | 复制后只 handleSelectAlbum |
| refreshAllCounters 并行拉取 4 个 API | ❌ | 函数不存在，refreshAppData 只拉取 2 个 API |

**修复建议**:
1. 创建 `refreshAllCounters` 函数，并行拉取 `getStats`/`getTree`/`getAlbums`/`getFavorites`
2. 在所有计数变化点调用该函数

---

### 问题 5：右键菜单通用化

**通过**: 0/5

| 验收项 | 状态 | 说明 |
|--------|------|------|
| 所有右键菜单文案用 t() 国际化 | ❌ | PhotoCard/DirectoryTree 硬编码中文 |
| PhotoCard/Sidebar/DirectoryTree/App 用菜单工厂函数 | ❌ | 各自内联构建 groups 数组 |
| 相册卡片右键弹菜单 | ❌ | 直接调用 handleAlbumAction('rename') |
| PhotoPreview 有右键菜单 | ❌ | 无 ContextMenu 组件引用 |
| ContextMenu 有入场动画 | ❌ | 无 animate-fadeIn/animate-modal-in |

**修复建议**:
1. 创建菜单工厂函数统一构建 ContextMenu groups
2. 所有文案改用 `t()` 国际化
3. PhotoPreview 添加右键菜单
4. ContextMenu 添加入场动画

---

### 问题 6：排序逻辑统一

**通过**: 0/7

| 验收项 | 状态 | 说明 |
|--------|------|------|
| sortOptions 无"按导入日期排序" | ❌ | 包含 import_date_desc/import_date_asc |
| 时间线选"日期升序"时，日期组从旧→新排列 | ❌ | groupPhotosByDay 固定降序 |
| 时间线选"日期降序"时，日期组从新→旧排列 | ⚠️ | 默认降序正确，但切换升序不改变顺序 |
| MainContent 文件夹视图 sort 生效 | ❌ | App.tsx 未传 onSortChange |
| MainContent 相册视图 sort 生效 | ❌ | 同上 |
| MainContent 收藏视图 sort 生效 | ❌ | 同上 |
| MainContent 切换 sort 后照片重新加载 | ❌ | 未连接 onSortChange |

**修复建议**:
1. 从 sortOptions 移除 import_date 相关选项
2. groupPhotosByDay 需响应 sort 状态动态排序
3. App.tsx 需连接 onSortChange 触发照片重新加载

---

### 问题 7：相册封面策略 + 默认封面重新设计

**通过**: 3/8

| 验收项 | 状态 | 说明 |
|--------|------|------|
| 有照片的相册自动显示最新照片作为封面 | ❌ | 后端未实现自动选择最新照片逻辑 |
| 无照片的相册显示默认封面（拍立得堆叠风格） | ✓ | 有 tile-default/cover-default/thumb-default |
| 默认封面无 emoji 和 "PHOTOS" 文字 | ❌ | 有 📷 emoji 和 "PHOTOS" 文字 |
| 默认封面亮色模式：白色背景 + 深灰线条 | ❌ | 使用 cyan 渐变背景 |
| 默认封面暗色模式：深色背景 + 浅灰线条 | ❌ | 无"浅灰线条"设计 |
| 默认封面在 3 个尺寸下都正确渲染 | ✓ | 有 3 种尺寸变体 |
| 切换主题时默认封面颜色自动适配 | ✓ | 使用 .dark CSS 选择器 |
| 所有默认封面均引用 AlbumCoverDefault 组件 | ❌ | 不存在 AlbumCoverDefault 组件 |

**修复建议**:
1. 创建 `AlbumCoverDefault` 组件，替代内联 emoji/label
2. 重新设计默认封面为拍立得堆叠风格
3. 后端实现自动选择最新照片作为封面

---

## 测试执行结果

### 前端测试
- **状态**: ⚠️ 无测试配置
- **说明**: package.json 中未配置 test 脚本

### 后端测试
- **状态**: ✅ 全部通过
- **通过数**: 746/746
- **耗时**: 30.03 秒
- **警告**: 1 个（locale.getdefaultlocale 将在 Python 3.15 中移除）

---

## 代码审核结果

### 文件存在性
- **存在**: 16/18 文件
- **缺失**: 
  - `frontend/src/components/common/menuBuilders.ts`
  - `frontend/src/components/common/AlbumCoverDefault.tsx`

### 主要问题
1. API 层 sort 参数支持不完整（getPhotos/getAlbumPhotos/getFavorites 前端未传递 sort）
2. refreshAllCounters 函数不存在
3. 缺少菜单工厂函数和默认封面组件

---

## 结论与建议

### 当前状态
**Spec 实现完成度**: 11.4% (5/44 验收项通过)

### 优先级排序
1. **P0 - 阻塞性问题**:
   - 问题 4: refreshAllCounters 函数缺失（影响所有计数刷新）
   - 问题 7: AlbumCoverDefault 组件缺失（影响默认封面）

2. **P1 - 核心功能**:
   - 问题 1: 布局切换逻辑错误（网格/瀑布流未实现）
   - 问题 2: 加入相册弹窗结构错误
   - 问题 6: 排序逻辑不生效

3. **P2 - 体验优化**:
   - 问题 3: 照片预览动效缺失
   - 问题 5: 右键菜单未统一

### 下一步行动
1. 创建缺失的组件（AlbumCoverDefault、menuBuilders）
2. 实现 refreshAllCounters 函数
3. 重构布局切换逻辑（displayMode → layoutMode）
4. 重写 JoinAlbumModal 对齐 v3 原型
5. 实现瀑布流 CSS（column-width: 200px）
6. 添加照片预览动效
7. 统一右键菜单工厂函数
8. 修复排序逻辑（sort 传后端 + 组间排序响应 sort）

---

**报告生成时间**: 2026-06-27  
**验收工具**: 并行 3 个 AI Agent（代码审核、测试执行、验收检查）
