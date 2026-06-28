# 🔍 Blur Arc 快速参考卡 v0.6.0

> 一页纸速查：常用命令、关键路径、API 速记、调试要点。
>
> **版本**：v0.6.0（2026-06-24）

---

## 🚀 启动

| 场景 | 命令 |
|------|------|
| PC 端（生产模式） | `python src/BlurArc.py` |
| PC 前端 dev 模式 | `cd frontend && npm run dev` |
| PC 端 + 前端 build | `cd frontend && npm run build && cd .. && python src/BlurArc.py` |
| 移动端（真机/模拟器） | `cd blurarc_app && flutter run` |
| 移动端 + hot reload | `cd blurarc_app && flutter run --hot` |
| 快捷菜单 | `.\scripts\dev-start.ps1` |

---

## 🧪 测试

| 套件 | 命令 |
|------|------|
| 后端全量 | `pytest` |
| 后端单元 | `pytest test/unit/ -v` |
| PC 前端类型检查 | `cd frontend && npx tsc --noEmit` |
| 移动端 | `cd blurarc_app && flutter test` |
| 移动端静态分析 | `cd blurarc_app && flutter analyze` |

---

## 📁 关键路径

| 用途 | 位置 |
|------|------|
| 相册根目录 | 用户自选（运行时确定） |
| 归档子目录 | `{相册根}/YYYY/YYYY-MM/` |
| 数据库（dev） | `项目根/.config/photo_manager.db` |
| 数据库（打包） | `exe所在目录/.config/photo_manager.db` |
| 缩略图缓存 | `~/.photomanager/thumbnails/`（用户主目录） |
| 用户配置 | `~/.photo_organizer_config.json` |
| FFmpeg | `backend/ffmpeg_binaries/ffmpeg.exe` |
| PC 端主入口 | `src/BlurArc.py` |
| PC 端 API | `backend/api_server.py` |
| 移动端 API | `backend/mobile_access_server.py` |
| mDNS 广播 | `backend/zeroconf_publisher.py` |
| 移动端入口 | `blurarc_app/lib/main.dart` |

---

## 🌐 端口

| 端口 | 用途 |
|------|------|
| **23986** | PC 端 WebView 服务（PyWebView 启动 Flask 在此端口） |
| **8900** | 移动接入服务（PC 端作为 mDNS 广播的 HTTP 服务） |
| **5353 / 5354** | mDNS（组播 224.0.0.251 / 单播回退） |

---

## 🧠 关键 API 速记

### PC 端（35+ 端点）

```
GET  /api/health
GET  /api/album/stats | /api/album/tree | /api/album/photos?path=...
GET  /api/album/thumbnail?path=... | /api/album/preview?path=...
POST /api/import/check | /api/import/start | /api/import/progress/<id>
POST /api/import/pause/<id> | /api/import/resume/<id>
POST /api/files/delete
GET  /api/settings | POST /api/settings
GET  /api/import/config | POST /api/import/config
```

### 移动端（20+ 端点）

```
# 配对
POST /api/mobile/pairing/start           # PC 端发起
GET  /api/mobile/pairing/pending         # 轮询配对码
POST /api/mobile/pairing/confirm         # PC 端确认
POST /api/mobile/pairing/request         # 移动端发起
POST /api/mobile/pairing/submit-code     # 移动端提交码
GET  /api/mobile/pairing/status/<id>     # 移动端轮询结果

# 浏览
GET  /api/mobile/photos/sections                  # 月份分组
GET  /api/mobile/photos/by-month?ym=YYYY-MM        # 单月
GET  /api/mobile/folder-tree                      # 文件夹树
GET  /api/mobile/thumbnail?path=...&token=...      # 缩略图
GET  /api/mobile/preview?path=...&token=...        # 中等预览
GET  /api/mobile/file?path=...&token=...           # 原图

# 上传
POST /api/mobile/upload                  # multipart 文件
POST /api/mobile/upload/done             # 通知 PC 端完成（弹 ImportDialog）
GET  /api/mobile/pending-flutter-uploads # 列出未导入
POST /api/mobile/import-batch            # PC 端确认导入

# 设备管理
GET  /api/mobile/devices                 # 已配对列表
POST /api/mobile/revoke                  # 撤销
GET  /api/mobile/status                  # 服务开关
```

---

## 🗃️ 数据库表速查

| 表 | 用途 | 关键字段 |
|----|------|----------|
| `media` | 媒体主表 | id, path, md5_hash, file_size, media_type, taken_at, exif_data |
| `import_jobs` | 导入任务 | id, status, total/new/skipped/duplicate, started_at, finished_at |
| `import_items` | 导入明细 | id, job_id, src_path, dest_path, status, error |
| `settings` | 设置 KV | key, value |
| `mobile_pairing` | 配对会话 | code, status, device_name, token, expires_at |
| `mobile_devices` | 已配对设备 | device_id, name, platform, token, paired_at, last_seen |
| `flutter_uploads` | 待导入上传 | id, device_id, file_path, sha256, created_at, imported |

ORM 在 `backend/database.py`，详见 [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)。

---

## ⚡ 性能优化要点

| 优化项 | 关键文件 / 函数 |
|--------|----------------|
| 两阶段预筛 | `import_manager._prescan_index()` |
| MD5 缓存复用 | `import_manager._import_file(md5_cache=...)` |
| 并行去重 | `ThreadPoolExecutor` in `import_manager.py` |
| 缩略图缓存 | `~/.photomanager/thumbnails/` + `thumbnail_manager.py` |
| mDNS 零配置 | `zeroconf_publisher.py` + Flutter `mdns_discovery.dart` |
| 移动端首屏 | `api_client.dart` 的 `Dio(sendTimeout: 30s)` |

---

## 🐛 调试速记

### mDNS 失败

```python
# 后端
from backend.zeroconf_publisher import ZeroconfPublisher
p = ZeroconfPublisher()
p.start()
print(p.wait_ready(timeout=3))   # True = 启动成功
print(p._last_error)              # 失败原因
```

### 移动端连不上 PC

- 同 WiFi？
- PC 防火墙 8900 端口放行？
- 模拟器只能手动输 `10.0.2.2:8900`？

### 导入慢

- 看进度条：是否在算 MD5
- 配 `prescan_index` 命中 DB 缓存（`prescan_index` 已改三元组）
- 大量文件可暂停

### PC 前端改了不生效

```bash
# 必须先 build 才会被 PyWebView 加载
cd frontend && npm run build
```

### Flutter 改了看不到效果

- hot reload: 按 `r`
- hot restart: 按 `R`
- 完整重启: 停掉 `flutter run` 再起

---

## 📐 模块地图

| 想改什么 | 改哪 |
|----------|------|
| PC 端窗口/启动 | `src/BlurArc.py` |
| PC 端 API 端点 | `backend/api_server.py` |
| 导入/去重逻辑 | `backend/import_manager.py` |
| 缩略图生成 | `backend/thumbnail_manager.py` |
| 视频处理 | `backend/video_processor.py` |
| 数据库模型 | `backend/database.py` |
| 用户配置 | `backend/config_manager.py` |
| 移动接入 API | `backend/mobile_access_server.py` |
| mDNS 广播 | `backend/zeroconf_publisher.py` |
| PC 端 UI 组件 | `frontend/src/components/` |
| 移动端页面 | `blurarc_app/lib/screens/` |
| 移动端 API 调用 | `blurarc_app/lib/services/api_client.dart` |
| 移动端主题 | `blurarc_app/lib/theme/` |

---

## 📝 发布流程（v0.5.3 范式）

1. 改代码 → 跑测试 → `cd frontend && npm run build`
2. 更新 `frontend/package.json` + `src/BlurArc.py` 版本号
3. 写 `CHANGELOG.md`（修复/变更/新增三段）
4. 写 `docs/superpowers/specs/<date>-vX.Y.Z-release-design.md` + `plans/<date>-vX.Y.Z-release.md`
5. `git add .` → `git commit -m "release: vX.Y.Z"` → `git push`
6. `git tag -a vX.Y.Z -m "Release vX.Y.Z — <主题>"` → `git push origin vX.Y.Z`
7. 跑 8 条 AC
8. GitHub 网页手动建 Release

---

## 📚 文档索引

- [README.md](../README.md) — 项目主入口
- [CHANGELOG.md](../CHANGELOG.md) — 版本变更
- [blurarc_app/README.md](../blurarc_app/README.md) — 移动端
- [QUICK_START.md](QUICK_START.md) — 5 分钟上手
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) — 项目总览
- [CODE_MAP.md](CODE_MAP.md) — 模块地图
- [API_REFERENCE.md](API_REFERENCE.md) — API 详细
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) — 开发指南
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) — 表结构
- [DEPENDENCIES.md](DEPENDENCIES.md) — 依赖

---

**版本**: v0.6.0 · **更新日期**: 2026-06-24
