# 软件截图存档

> 本目录用于保存 Blur Arc 的官方软件截图，作为 README、官网落地页、社交媒体、海报配图等场景的素材。
>
> **更新日期**: 2026-06-23（v0.5.3 同步 — 加入移动端 / 平板）

## 文件清单

### 🖥️ PC 端

| 文件名 | 说明 |
|---|---|
| `01-welcome.png` | 首次启动欢迎页：相机图标 + 「欢迎使用 Blur Arc」+ 「选择相册文件夹」主操作按钮 + 隐私本地化提示文案 |
| `02-main-view.png` | 主相册浏览视图：左侧 280px 侧边栏（总文件个数 / 总文件大小 / 照片统计 / 导入照片按钮），右侧照片网格（封面缩略图 + 「选择」入口 + 顶栏主题切换） |
| `03-import-preview.png` | 导入预览对话框：路径 + 总文件个数 / 总文件大小 + 时间线 / 已在相册 / 文件夹内重复 三个标签页 + 日期筛选 + 照片预览 + 「开始导入」操作 |

### 📱 移动端 (v0.5.2+)

| 文件名 | 说明 |
|---|---|
| `flutter_web_app.png` | Flutter Web 构建截图（v3 主框架） |
| `flutter_web_final.png` | Flutter Web 最终版截图 |
| `mobile-connect-dark.png` | 移动端连接页（暗色）— mDNS 扫描 + 手动输入 IP |
| `mobile-connect-light.png` | 移动端连接页（亮色） |
| `mobile-home-dark.png` | 移动端首页（暗色）— 月份分组照片墙 |
| `mobile-home-light.png` | 移动端首页（亮色） |
| `mobile-upload-dark.png` | 移动端上传页（暗色） |
| `mobile-settings-dark.png` | 移动端设置页（暗色） |
| `mobile-pairing-code.png` | 配对码输入页（6 位数字键盘） |

### 📲 平板 (v0.5.2+)

| 文件名 | 说明 |
|---|---|
| `tablet-home-light.png` | 平板首页（亮色）— 侧边栏 + 主内容 |
| `tablet-home-dark.png` | 平板首页（暗色） |
| `tablet-photo-grid-light.png` | 平板照片网格（亮色） |
| `tablet-settings.png` | 平板设置页 |

### 🔄 流程截图

| 文件名 | 说明 |
|---|---|
| `flow-pairing-1-mobile.png` | 配对流程：手机发现 PC |
| `flow-pairing-2-pc.png` | 配对流程：PC 端弹配对码 |
| `flow-pairing-3-mobile.png` | 配对流程：手机输入配对码 |
| `flow-pairing-4-success.png` | 配对流程：配对成功 |
| `flow-upload-1-mobile.png` | 上传流程：手机选图 |
| `flow-upload-2-pc.png` | 上传流程：PC 端弹 ImportDialog |

## 使用建议

### 场景一：README / 落地页主图
- **PC 端**：`02-main-view.png`（最能体现相册管理能力）
- **移动端**：`mobile-home-dark.png`（最完整的移动端体验）
- **双端并排**：用 `_compare/` 下的截图

### 场景二：强调「本地 / 隐私 / 去重」
- 使用 `03-import-preview.png`（直接在 UI 内展示了「已在相册 / 文件夹内重复」两个去重视图）

### 场景三：移动端教程 / 博客
- 配对流程：`flow-pairing-*.png`（4 张完整序列）
- 上传流程：`flow-upload-*.png`

### 场景四：海报 / 宣传物料
- 以本目录截图为基础，结合 `docs/posters/poster.png` 主视觉使用

## 命名与维护约定

- 编号顺序与产品使用流程一致：欢迎 → 浏览 → 导入。
- 平台前缀：`mobile-` / `tablet-` / `flow-` 区分场景。
- 主题后缀：`-dark` / `-light`（同界面双主题时分别建文件）。
- 后续新增截图请沿用上述命名规范。
- 修改 UI 后请同步更新本 README 中的「说明」一栏。

## 自动化截图建议

### PC 端

```bash
# 启动 dev 模式
cd frontend && npm run dev
# 浏览器手动截 1440x900（标准桌面分辨率）
```

### 移动端

```bash
# Flutter 截屏
cd blurarc_app
flutter run -d <device-id>
# 模拟器截屏快捷键：
#   iOS: Cmd+S
#   Android: Ctrl+S（在 Emulator Extended Controls）

# 批量截：
flutter drive --target=test_driver/screenshot.dart
```

> 导出 1x PNG（避免 Retina 模糊），使用 PNG 压缩工具（pngquant）优化文件大小。

## 相关资源

- [docs/prototypes/](docs/prototypes/) — UI 原型（设计阶段）
- [docs/prototypes/_compare/](docs/prototypes/_compare/) — 原型 vs 实现对比

---

**最后更新**: 2026-06-23 (v0.5.3 文档同步)
