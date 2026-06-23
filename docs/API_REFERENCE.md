# API 参考文档

> 更新日期：2026-06-23
> 版本：v0.5.3
>
> 包含 **PC 端** (`http://localhost:23986`) 与 **移动端** (`http://<PC_IP>:8900`) 的所有 REST 端点。

## 基础信息

- **PC 端 Base URL**: `http://localhost:23986`（PyWebView 嵌入时使用相对路径）
- **移动端 Base URL**: `http://<PC_IP>:8900`（移动端 App 通过 mDNS 发现 PC）
- **数据格式**: JSON
- **编码**: UTF-8
- **鉴权**：
  - PC 端：无（本地）
  - 移动端：Bearer Token（配对后获得），从 `/api/mobile/pairing/confirm` 返回

---

## 相册操作

### GET /api/health

健康检查

**响应**
```json
{
  "status": "ok",
  "message": "Server is running"
}
```

---

### GET /api/album/stats

获取相册统计信息

**响应**
```json
{
  "total_photos": 1234,
  "total_videos": 56,
  "total_size": 1234567890,
  "date_range": {
    "earliest": "2020-01-15",
    "latest": "2024-06-10"
  },
  "by_year": {
    "2024": 500,
    "2023": 400
  }
}
```

---

### GET /api/album/tree

获取目录树结构

**响应**
```json
{
  "name": "相册目录",
  "path": "/path/to/album",
  "children": [
    {
      "name": "2024",
      "path": "/path/to/album/2024",
      "children": [
        {
          "name": "2024-03",
          "path": "/path/to/album/2024/2024-03",
          "count": 150
        }
      ]
    }
  ]
}
```

---

### GET /api/album/photos

获取照片列表

**参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 否 | 目录路径，默认根目录 |
| page | int | 否 | 页码，默认 1 |
| per_page | int | 否 | 每页数量，默认 100 |
| sort | string | 否 | 排序字段：date/size/name |
| order | string | 否 | 排序方向：asc/desc |

**响应**
```json
{
  "photos": [
    {
      "id": 1,
      "filename": "20240615_143022_001.jpg",
      "path": "/path/to/photo.jpg",
      "thumbnail_url": "/api/album/thumbnail?path=...",
      "preview_url": "/api/album/preview?path=...",
      "url": "/api/album/file?path=...",
      "size": 1234567,
      "media_date": "2024-06-15T14:30:22",
      "file_type": "photo",
      "extension": ".jpg"
    }
  ],
  "total": 1234,
  "page": 1,
  "per_page": 100,
  "total_pages": 13
}
```

---

### GET /api/album/thumbnail

获取缩略图

**参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 文件路径 |
| size | string | 否 | 尺寸：small/medium/large，默认 medium |

**响应**
- Content-Type: `image/jpeg`
- 缓存头已设置

---

### GET /api/album/preview

获取预览图（HEIC 等特殊格式转 JPEG）

**参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 文件路径 |

---

### GET /api/album/file

获取原始文件（支持 HTTP Range）

**参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 文件路径 |

**特性**
- 支持 Range 请求（视频拖动进度条）
- 自动设置 Content-Type

---

### GET /api/album/exif

获取 EXIF 信息

**参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 文件路径 |

**响应**
```json
{
  "Make": "Apple",
  "Model": "iPhone 15 Pro",
  "DateTimeOriginal": "2024:06:15 14:30:22",
  "ExposureTime": "1/120",
  "FNumber": "f/1.8",
  "ISOSpeedRatings": 100,
  "FocalLength": "6.0 mm",
  "GPSLatitude": 39.9042,
  "GPSLongitude": 116.4074
}
```

---

## 导入操作

### POST /api/import/check

导入预检（异步）

**请求**
```json
{
  "source_path": "/path/to/source",
  "target_path": "/path/to/album",
  "skip_source_duplicates": true,
  "skip_target_duplicates": true
}
```

**响应**
```json
{
  "check_id": "check_abc123",
  "status": "started"
}
```

---

### GET /api/import/check/progress/<check_id>

获取预检进度

**响应**
```json
{
  "check_id": "check_abc123",
  "status": "processing",
  "progress": 0.75,
  "total_files": 1000,
  "processed_files": 750,
  "new_files": 800,
  "source_duplicates": 100,
  "target_duplicates": 100
}
```

---

### POST /api/import/start

启动导入

**请求**
```json
{
  "source_path": "/path/to/source",
  "target_path": "/path/to/album",
  "import_mode": "copy",
  "skip_source_duplicates": true,
  "skip_target_duplicates": true
}
```

**响应**
```json
{
  "import_id": "import_xyz789",
  "status": "started"
}
```

---

### GET /api/import/progress/<import_id>

获取导入进度

**响应**
```json
{
  "import_id": "import_xyz789",
  "status": "processing",
  "progress": 0.5,
  "total_files": 1000,
  "imported_files": 500,
  "skipped_files": 50,
  "failed_files": 2,
  "duplicated_files": 10,
  "total_size": 1234567890,
  "processed_size": 617283945,
  "current_file": "IMG_0501.jpg",
  "start_time": "2024-06-15T14:00:00",
  "elapsed_seconds": 120,
  "estimated_remaining_seconds": 120
}
```

---

### POST /api/import/pause/<import_id>

暂停导入

---

### POST /api/import/resume/<import_id>

继续导入

---

### POST /api/import/cancel/<import_id>

取消导入

---

## 文件操作

### POST /api/files/delete

批量删除文件

**请求**
```json
{
  "paths": [
    "/path/to/file1.jpg",
    "/path/to/file2.jpg"
  ]
}
```

**响应**
```json
{
  "deleted": 2,
  "failed": 0,
  "errors": []
}
```

---

## 设置操作

### GET /api/settings/album-path

获取相册路径

**响应**
```json
{
  "album_path": "/path/to/album"
}
```

---

### PUT /api/settings/album-path

设置相册路径

**请求**
```json
{
  "album_path": "/new/path/to/album"
}
```

---

### GET /api/settings/ffmpeg-status

获取 FFmpeg 状态

**响应**
```json
{
  "available": true,
  "version": "8.1.1",
  "path": "/path/to/ffmpeg.exe"
}
```

---

### GET /api/settings/theme

获取主题设置

**响应**
```json
{
  "theme": "light"
}
```

---

### PUT /api/settings/theme

设置主题

**请求**
```json
{
  "theme": "dark"
}
```

---

## 视频操作

### GET /api/video/metadata

获取视频元数据

**参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| path | string | 是 | 视频文件路径 |

**响应**
```json
{
  "duration": 120.5,
  "width": 1920,
  "height": 1080,
  "codec": "h264",
  "bit_rate": 5000000,
  "frame_rate": "30/1",
  "format": "mov,mp4,m4a,3gp,3g2,mj2",
  "size": 75625000
}
```

---

## 缓存操作

### POST /api/cache/cleanup

清理缓存

**请求**
```json
{
  "type": "thumbnails",
  "older_than_days": 30
}
```

---

## 移动端 API（v0.5.2+）

> **Base URL**: `http://<PC_IP>:8900`
> **鉴权**: 配对后返回的 Token，需在 Header `Authorization: Bearer <token>` 中携带
> 静态资源端点（缩略图/原图）支持 `?token=...` query 形式以兼容 `<img src>` 标签

### 配对

#### POST /api/mobile/pairing/start

PC 端发起配对，生成 6 位配对码。

**请求**：无

**响应**：
```json
{
  "ok": true,
  "code": "482913",
  "session_id": "uuid-xxx",
  "expires_in": 300
}
```

---

#### GET /api/mobile/pairing/pending

轮询等待手机输入的配对码（PC 端用，5s 一次）。

**响应**：
```json
{
  "ok": true,
  "has_pending": true,
  "code": "482913",
  "session_id": "uuid-xxx",
  "device_name": "Alice's iPhone"
}
```

---

#### POST /api/mobile/pairing/confirm

PC 端确认配对，返回 Token。

**请求**：
```json
{ "session_id": "uuid-xxx" }
```

**响应**：
```json
{
  "ok": true,
  "device_id": "dev-xxx",
  "token": "eyJhbGciOiJIUzI1...",
  "expires_at": "2026-07-23T10:00:00Z"
}
```

---

#### POST /api/mobile/pairing/request

移动端发起配对请求（携带设备名）。

**请求**：
```json
{ "device_name": "Alice's iPhone", "platform": "android" }
```

**响应**：
```json
{ "ok": true, "session_id": "uuid-xxx" }
```

---

#### POST /api/mobile/pairing/submit-code

移动端提交 6 位配对码。

**请求**：
```json
{ "session_id": "uuid-xxx", "code": "482913" }
```

**响应**：
```json
{
  "ok": true,
  "status": "approved",
  "device_id": "dev-xxx",
  "token": "eyJ..."
}
```

---

#### GET /api/mobile/pairing/status/<session_id>

移动端轮询配对结果。

**响应**：
```json
{ "ok": true, "status": "pending|approved|rejected|expired" }
```

### 浏览

#### GET /api/mobile/photos/sections

获取按月份分组的照片列表（移动端首页用）。

**Header**: `Authorization: Bearer <token>`

**响应**：
```json
{
  "ok": true,
  "sections": [
    {
      "ym": "2026-06",
      "count": 42,
      "cover": "2026/2026-06/20260615_140322_001.jpg"
    }
  ]
}
```

---

#### GET /api/mobile/photos/by-month?ym=YYYY-MM

获取某月所有照片。

**Header**: `Authorization: Bearer <token>`

**响应**：
```json
{
  "ok": true,
  "ym": "2026-06",
  "photos": [
    {
      "id": 123,
      "path": "2026/2026-06/20260615_140322_001.jpg",
      "size": 1234567,
      "media_type": "photo",
      "taken_at": "2026-06-15T14:03:22",
      "width": 4032,
      "height": 3024
    }
  ]
}
```

---

#### GET /api/mobile/folder-tree

获取文件夹树（按 `YYYY/YYYY-MM/`）。

**Header**: `Authorization: Bearer <token>`

**响应**：与 PC 端 `/api/album/tree` 相同结构。

### 资源获取（带 Token 鉴权）

#### GET /api/mobile/thumbnail?path=...

获取缩略图（移动端首页/列表用）。

**鉴权**：`?token=...` query 或 Header

**响应**：image/jpeg 二进制

---

#### GET /api/mobile/preview?path=...

获取中等预览（约 2000px 长边）。

**响应**：image/jpeg 二进制

---

#### GET /api/mobile/file?path=...

获取原图/原视频（用于下载到本地）。

**响应**：原始文件二进制

### 上传

#### POST /api/mobile/upload

上传单个文件（multipart/form-data）。

**Header**: `Authorization: Bearer <token>`

**Form 字段**：
- `file`：文件二进制
- `taken_at`：可选，拍摄时间 ISO 8601

**响应**：
```json
{
  "ok": true,
  "file_path": "inbox/20260615_140322_001.jpg",
  "sha256": "abc..."
}
```

---

#### POST /api/mobile/upload/done

通知 PC 端本次上传完成（触发 ImportDialog 弹窗）。

**请求**：
```json
{ "device_id": "dev-xxx", "count": 5 }
```

**响应**：
```json
{ "ok": true, "import_id": "uuid-xxx" }
```

---

#### GET /api/mobile/pending-flutter-uploads

列出所有来自 Flutter 移动端、尚未导入的上传批次。

**Header**: `Authorization: Bearer <token>`

**响应**：
```json
{
  "ok": true,
  "pending": [
    {
      "import_id": "uuid-xxx",
      "device_id": "dev-xxx",
      "device_name": "Alice's iPhone",
      "count": 5,
      "created_at": "2026-06-15T14:30:00"
    }
  ]
}
```

---

#### POST /api/mobile/import-batch

PC 端确认导入某个上传批次（用户在 ImportDialog 点确认）。

**请求**：
```json
{ "import_id": "uuid-xxx" }
```

**响应**：
```json
{ "ok": true, "imported": 5 }
```

### 设备管理

#### GET /api/mobile/devices

列出所有已配对设备。

**响应**：
```json
{
  "ok": true,
  "devices": [
    {
      "device_id": "dev-xxx",
      "name": "Alice's iPhone",
      "platform": "android",
      "paired_at": "2026-06-15T10:00:00",
      "last_seen": "2026-06-23T14:30:00"
    }
  ]
}
```

---

#### POST /api/mobile/revoke

撤销单台设备的配对。

**请求**：
```json
{ "device_id": "dev-xxx" }
```

**响应**：`{ "ok": true }`

---

#### GET /api/mobile/status

移动接入服务开关与状态。

**响应**：
```json
{
  "ok": true,
  "enabled": true,
  "mdns_active": true,
  "port": 8900,
  "paired_count": 2
}
```

---

## 错误响应

所有错误响应格式：

```json
{
  "error": "错误类型",
  "message": "错误描述"
}
```

**常见错误码**

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权（移动端无 Token / Token 过期） |
| 403 | 禁止（设备被撤销） |
| 404 | 资源不存在 |
| 410 | 配对码过期 |
| 500 | 服务器内部错误 |
