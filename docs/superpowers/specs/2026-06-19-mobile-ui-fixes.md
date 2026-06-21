# 移动端 App 修复和 UI 优化任务

> 日期: 2026-06-19 | 状态: 待修复

---

## 问题 1：PC 端撤销已配对设备交互生硬

**文件：** `frontend/src/components/dialogs/MobileDeviceManager.tsx`

**当前表现：** 点击「撤销」按钮立即删除设备，没有任何确认提示。

**要求：** 点击「撤销」时弹出确认对话框，用户确认后才执行撤销操作。

**修改位置：** 大约第 198 行附近的 `revokeMobileDevice` 调用。参考已有的「撤销全部」交互风格。

```tsx
// 当前（太生硬）：
<button onClick={async () => { await api.revokeMobileDevice(d.token); loadStatus(); }} className="...">

// 要求改为先弹窗确认再执行
```

---

## 问题 2：手机端缩略图加载失败

**文件：** `backend/mobile_access_server.py` 第 408-425 行

**当前表现：** `/api/mobile/thumbnail` 返回 HTTP 500。`/api/mobile/preview` 正常（HTTP 200 可正常返回图片）。说明路径验证和权限都没问题，是 `get_thumbnail_sync()` 调用出了问题。

**排查建议：** `get_thumbnail_sync` 调用链可能依赖 Flask 应用上下文或某些仅在主 Flask 应用中初始化的状态。移动端 Flask 是独立实例，需要排查兼容性。

**测试验证：**
```bash
TOKEN="xxx"  # 替换为有效 token
curl -H "Authorization: Bearer $TOKEN" \
  "http://192.168.31.164:8900/api/mobile/thumbnail?path=你的照片路径"
```

---

## 问题 3：手机端首页 UI 重做

**文件：** 主要涉及 `blurarc_app/lib/screens/` 和 `blurarc_app/lib/widgets/` 目录

### 当前问题

- `AlbumScreen` 目前展示的是后端原始目录树 (`TreeView`)，不是最终设计
- 整体暗色主题风格不够精细，缺少圆角、间距、图标等细节
- 三个 Tab 的内容不符合用户预期

### 设计要求

参考以下设计细节实现手机端 App（Flutter，Material Dark 主题，主色 `#22D3EE`）：

#### 底部三个 Tab

| Tab | 图标 | 说明 |
|-----|------|------|
| 🖼 相册 | `Icons.photo` | 默认首页 |
| 📤 上传 | `Icons.upload` | 上传照片到 PC |
| ⚙️ 设置 | `Icons.settings` | 主题 + 断开连接 |

当前 `HomePage`（`home_page.dart`）的三个 Tab 结构是对的，主要是内容和风格要改。

#### 🖼 相册 Tab

**不是目录树列表！** 而是**瀑布流网格**，效果类似 Google Photos：

- 照片网格，3 列，按 PC 端目录顺序分组
- 分隔线格式：`2025年6月`（中文年月格式），非年月目录直接显示目录名如 `Screenshots`
- 往下滚动自动加载更多（无限滚动）
- 右上角 📂 图标作为次要入口，点击切换为目录树视图
- 点击任意照片进入全屏预览（左右滑动翻页）

数据来源：
- `/api/mobile/photos?path=xxx` — 获取某个文件夹的照片列表（已有这个 API，当前因 MEDIA_FORMATS 导入问题失败已修复）
- 需要新增 `/api/mobile/photos/all?page=1&page_size=50` 接口（或复用现有数据），按目录顺序返回所有照片，每次返回一批照片，附带其所属目录名作为分隔线

**目录树视图**：当前 `TreeView`（`widgets/tree_view.dart`）可以保留，点击月目录/叶目录时跳转到照片网格。

**照片网格**：当前 `PhotoGridScreen` 已经实现了网格加载，但需要修复缩略图端点（见问题 2）

**全屏预览**：当前 `PhotoPreviewScreen` 已实现左右滑动翻页，`CachedNetworkImage` 使用 `getPreviewUrl`，预览端点 OK

#### 样式改进清单

1. **全局暗色主题**：`main.dart` 中 `ThemeData.dark(useMaterial3: true)` 已配置，但需统一卡片圆角（12px）、间距（16/24px）、图标颜色
2. **AppBar**：统一为无背景色（透明或与页面一致），标题字号 18，不要多余按钮
3. **大号图标 + 小字辅助信息** 的 page 布局风格
4. **圆形头像/图标**：配对码页面的图标等
5. **按钮**：FilledButton 用主色填充，次要操作用 TextButton
6. **颜色**：主色 `#22D3EE`，背景 `#0c1117`，卡片 `#151d26`，边框 `#1c2836`
7. **加载状态**：使用 CircularProgressIndicator（主色），不要空白页
8. **空状态**：显示对应图标和提示文字（如「此文件夹没有照片」已实现）

#### 已验证正常工作的后端 API

| 端点 | 状态 | 说明 |
|------|------|------|
| `GET /api/mobile/tree` | ✅ 已修 | 返回完整目录树 |
| `GET /api/mobile/photos?path=xxx` | ✅ 已修 | 返回路径下的照片列表 |
| `GET /api/mobile/preview?path=xxx` | ✅ 正常 | 返回预览图（HTTP 200） |
| `GET /api/mobile/thumbnail?path=xxx` | ❌ 待修 | 返回 500 |
| `GET /api/mobile/file?path=xxx` | ⚠️ 待测 | 原始文件 |
| `GET /api/mobile/exif?path=xxx` | ⚠️ 待测 | EXIF 数据 |
| `GET /api/mobile/verify` | ✅ 正常 | Token 验证 |
| `GET /api/mobile/stats` | ✅ 正常 | 相册统计 |
| `POST /api/mobile/upload` | ⚠️ 待测 | 上传照片 |

#### 需要新增或调整的 API

为了让相册 Tab 实现「按目录分组的瀑布流」，建议新增：

**`GET /api/mobile/photos/all?page=1&page_size=50`**
返回所有照片，按目录顺序分页，每页附带目录名信息：

```json
{
  "sections": [
    {"dir_name": "2026-06", "display_name": "2025年6月", "photos": [...]},
    {"dir_name": "2026-05", "display_name": "2025年5月", "photos": [...]}
  ],
  "total": 100,
  "page": 1,
  "total_pages": 2
}
```

对于 non-YYYY-MM 格式目录，`display_name` 直接用目录名。

---

## 执行优先级

1. **问题 1**（撤销确认）：简单，5 分钟
2. **问题 2**（缩略图 500）：中等，需要看 `get_thumbnail_sync` 的错误日志
3. **问题 3**（UI 重做）：大工程，分步做：
   - 3a：新增 `/api/mobile/photos/all` 端点
   - 3b：用瀑布流替换当前目录树作为默认首页视图
   - 3c：目录树作为次要入口（右上角图标切换）
   - 3d：整体样式打磨（主题、间距、圆角、颜色）
