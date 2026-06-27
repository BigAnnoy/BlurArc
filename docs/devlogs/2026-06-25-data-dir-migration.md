# v0.7 数据目录变更（解决"升级丢失数据"）

**日期**：2026-06-25
**议题**：用户每次更新 exe 后，数据库和配置文件被清空
**状态**：已决策，待 v0.7 实施

## 问题

`backend/config_manager.py` 的 `_get_app_data_dir()` 在打包模式下返回 `Path(sys.executable).parent` = `<exe>/` 目录：

```python
def _get_app_data_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent  # ← 根因
    return Path(__file__).parent.parent
```

数据库 (`<exe>/.config/photo_manager.db`)、配置 (`<exe>/.config/config.json`)、缩略图缓存 (`~/.photomanager/`) 都依赖这个目录。用户每次覆盖 `dist/BlurArc/` 时，**`.config/` 一并被覆盖**。

## 决策

| 项 | 决策 |
|----|------|
| 数据目录 | `~/Documents/BlurArc/`（我的文档）|
| 范围 | **所有用户数据统一**——DB / 配置 / 缩略图 / 临时 / 日志 / 移动设备数据 |
| 旧数据迁移 | **DB/配置不迁移**（用户手动重新导入）；**缩略图自动移动**（无意义成本低）|
| 实施版本 | v0.7 |
| 旧路径检测 | DB/配置只 toast；缩略图自动 move |

## 选"我的文档"的原因

1. 用户能直接看到（不用记 `%APPDATA%` 这种隐藏路径）
2. 系统重装/迁移方便（"我的文档"会被备份软件优先备份）
3. 卸载时不会误删（卸载 exe 不影响 Documents）
4. 跨平台一致（macOS / Linux 也用 `~/Documents/BlurArc/`）
5. **不分散**——一个根目录装下所有数据，备份/迁移最简单

## 目录结构

```
C:\Users\Alice\Documents\BlurArc\          ← 根：所有用户数据
├── .config\
│   ├── photo_manager.db                   # 主数据库
│   ├── config.json                        # 应用配置
│   ├── mobile_tokens.json                 # 手机配对 token
│   └── phone_upload\                      # 手机上传临时目录
├── thumbnails\                            # 缩略图缓存（跨相册共享）
├── cache\                                 # 其他缓存（v0.7 预留）
├── logs\                                  # 应用日志
└── exports\                               # 导出文件（v0.8+）
```

**v0.6 分散位置 → v0.7 全部收回**：
- `~/.photomanager/thumbnails/` → `~/Documents/BlurArc/thumbnails/`
- `~/.photo_organizer_config.json` → `~/Documents/BlurArc/.config/config.json`
- `<exe>/.config/...` → `~/Documents/BlurArc/.config/...`
- 系统临时目录（`%TEMP%/blurarc_*`）→ `~/Documents/BlurArc/cache/`

## 实施清单（v0.7）

- [ ] `backend/config_manager.py`
  - 新增 `_get_user_data_dir()` → `~/Documents/BlurArc/`
  - 替换 `_get_app_data_dir()` 实现
  - 首次启动建子目录：`.config/`, `thumbnails/`, `cache/`, `logs/`, `exports/`
- [ ] `backend/database.py` — DB_PATH 用新函数
- [ ] `backend/thumbnail_manager.py` — 缩略图目录迁移（`~/.photomanager/` → 新位置）
- [ ] `backend/phone_upload_server.py` / `mobile_access_server.py` — 临时/token 文件
- [ ] **全局清理**：搜索 `sys.prefix` / `%TEMP%` / 散落临时目录 → 统一 `~/Documents/BlurArc/cache/`
- [ ] `src/BlurArc.py` — 启动时检测旧路径
  - `<exe>/.config/` 存在 → toast 提示（不复制）
  - `~/.photomanager/` 存在 → 自动移动到新位置
- [ ] `docs/RELEASE_NOTES_v0.7.0.md` — 重大变更说明

## 测试用例

- [ ] 首次启动：自动创建 `~/Documents/BlurArc/{.config,thumbnails,cache,logs,exports}/`
- [ ] 导入照片：DB 写入新路径，缩略图存新位置
- [ ] 重启应用：数据保留
- [ ] 删除 exe（保留 Documents）：数据保留 ✅
- [ ] 升级 v0.6 → v0.7：旧 DB/配置不丢（虽然不会被读取）；旧缩略图自动移走 ✅

## 后续优化

v0.9+ 可加一次性迁移脚本 `blurarc.exe --migrate-from-v0.6`，自动把旧 DB/配置也搬过来。
