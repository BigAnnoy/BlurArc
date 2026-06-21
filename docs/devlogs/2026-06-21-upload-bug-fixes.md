# 2026-06-21: 移动接入 Bug 修复 + 上传通知导入

---

## 照片显示问题诊断

手机端相册 Tab 只显示 2 张照片（PC 端实际有 6 张），缩略图/预览加载失败（403）。

**根因：**
- `mobile_access_server.py` 从 `api_server` 而非 `constants` 导入 `MEDIA_FORMATS`
- 数据库只有 2 条记录指向临时测试目录，其余照片未入库
- `sections` API 查询数据库而非文件系统

**修复：**
- `MEDIA_FORMATS` 导入改为 `from .constants import MEDIA_FORMATS`
- 重建索引后正常显示
- 注意：数据库不自动跟踪文件系统变更，依赖 `rebuild_index` 或导入流程

---

## 上传 HTTP 500 修复

### 根因

`TokenManager` 缺少 `get_upload_root()` 方法，`_handle_upload()` 调用时抛 `AttributeError` → Flask 返回 500。

### 修复（`backend/mobile_access_server.py`）

| 改动 | 说明 |
|------|------|
| TokenManager 新增 `_session_upload_dirs` 字典 + `get_upload_root(token)` | 按 token 分配上传目录，同 token 复用同一目录，不再每文件新建 |
| `start()` 防重入 + `_start_lock` | 已运行直接返回当前信息，锁保护防止竞态 |
| `threaded=False` → `True` | 支持并发请求，上传时其他端点不被阻塞 |
| `stop()` 清理 `_upload_counts` + `_session_upload_dirs` | 服务重启后重置会话状态 |

---

## 上传完成通知 → PC 端自动弹导入弹窗

### 背景

原设计文档规划了「手机推送完成后 PC 端弹 ImportDialog」，但从未实现。Flutter App 上传后 PC 无任何提示。

### 方案变更

`5 秒防抖` → `App 主动通知`：

- **初版：** 后端每收到一个文件就启动 5 秒定时器，文件流停 5 秒后通知前端
- **最终：** 去掉防抖，App 上传循环结束后主动调 `POST /api/mobile/upload/done`，后端立即通知
- **原因：** 5 秒间隔不可靠（用户传大文件时被误触发），App 自己知道何时完成

### 改动清单

| 文件 | 改动 |
|------|------|
| `backend/mobile_access_server.py` | 移除防抖；新增 `POST /api/mobile/upload/done` 端点，调用 `_notify_flutter_upload()` |
| `backend/api_server.py` | 新增 `_flutter_upload_sessions` + `_notify_flutter_upload()` + 2 个端点 |
| `frontend/src/App.tsx` | 轮询 pending-flutter-uploads，发现新会话自动打开 ImportDialog |
| `frontend/src/.../ImportDialog.tsx` | 新增 `phoneSourcePath` prop，打开时自动触发导入检查 |
| `frontend/src/services/api.ts` | `getPendingFlutterUploads()` + `clearPendingFlutterUpload()` |
| `blurarc_app/lib/services/api_client.dart` | 新增 `uploadDone()` |
| `blurarc_app/lib/screens/upload_screen.dart` | 上传循环成功后调 `api.uploadDone()` |

### 完整流程

```
1. Flutter App 上传 N 张照片（逐张 POST /api/mobile/upload）
2. 上传循环结束 → App 调 POST /api/mobile/upload/done
3. 后端收到 → 调用 _notify_flutter_upload → 存入 _flutter_upload_sessions
4. 前端轮询 GET /api/mobile/pending-flutter-uploads（每 3 秒）
5. 发现有新会话 → 立即清除后端通知 → 自动打开 ImportDialog
6. ImportDialog 接收 phoneSourcePath → 自动开始导入检查
7. 用户预览 → 确认导入 → 完成
```

### 数据流

```
手机 App ──POST /upload/done──→ 移动接入服务 (8900-8999)
                                         │
                                  _notify_flutter_upload()
                                         │
                                  _flutter_upload_sessions[upload_dir]
                                         │
PC 前端轮询 GET /pending-flutter-uploads ─→ ImportDialog 自动打开
                                         │
                                  导入完成 → refreshAppData()
```
