# 数据库模型文档

> 更新日期：2026-06-16
> 数据库类型：SQLite
> ORM：SQLAlchemy

## 数据库文件位置

- **开发模式**：`项目根目录/.config/photo_manager.db`
- **打包模式**：`exe所在目录/.config/photo_manager.db`

---

## 数据表

### photos（照片/视频表）

主要数据表，存储所有导入的媒体文件信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| filename | VARCHAR(255) | NOT NULL | 文件名 |
| path | TEXT | NOT NULL, UNIQUE | 完整路径（唯一约束） |
| size | INTEGER | NOT NULL | 文件大小（字节） |
| md5_hash | VARCHAR(32) | INDEX | MD5 哈希值（允许重复，支持 _dup 副本） |
| created_at | DATETIME | DEFAULT NOW | 记录创建时间 |
| modified_at | DATETIME | ON UPDATE | 记录修改时间 |
| media_date | DATETIME | - | 媒体拍摄日期（EXIF/视频元数据） |
| file_type | VARCHAR(10) | NOT NULL | 文件类型：photo/video |
| extension | VARCHAR(10) | NOT NULL | 文件扩展名 |
| thumbnail_path | TEXT | - | 缩略图路径 |
| imported_at | DATETIME | DEFAULT NOW | 导入时间 |
| is_favorite | BOOLEAN | DEFAULT FALSE | 是否收藏 |

**索引**
- `id`: 主键索引
- `path`: 唯一索引
- `md5_hash`: 普通索引（用于去重查询）

---

### import_history（导入历史表）

记录每次导入操作的历史。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| source_path | TEXT | NOT NULL | 源目录路径 |
| target_path | TEXT | NOT NULL | 目标相册路径 |
| total_files | INTEGER | NOT NULL | 总文件数 |
| imported_files | INTEGER | NOT NULL | 已导入数 |
| skipped_files | INTEGER | NOT NULL | 跳过数 |
| failed_files | INTEGER | NOT NULL | 失败数 |
| total_size | INTEGER | - | 总字节数 |
| start_time | DATETIME | DEFAULT NOW | 开始时间 |
| end_time | DATETIME | - | 结束时间 |
| status | VARCHAR(20) | NOT NULL | 状态 |

**status 取值**
| 值 | 说明 |
|----|------|
| pending | 等待中 |
| processing | 处理中 |
| completed | 已完成 |
| failed | 失败 |
| cancelled | 已取消 |

---

### settings（设置表）

存储应用配置。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| key | VARCHAR(50) | NOT NULL, UNIQUE | 设置键 |
| value | TEXT | NOT NULL | 设置值 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |
| updated_at | DATETIME | ON UPDATE | 更新时间 |

**默认设置**
| key | value | 说明 |
|-----|-------|------|
| import_mode_default | copy | 默认导入模式 |
| thumbnail_size | 200x200 | 缩略图尺寸 |
| cache_duration | 3600 | 缓存时长（秒） |
| dark_mode | false | 深色模式 |

---

### tags（标签表）- 预留

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| name | VARCHAR(50) | NOT NULL, UNIQUE | 标签名 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

---

### photo_tags（照片-标签关联表）- 预留

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| photo_id | INTEGER | FK, PK | 照片 ID |
| tag_id | INTEGER | FK, PK | 标签 ID |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

---

### albums（相册表）- 预留

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主键 |
| name | VARCHAR(100) | NOT NULL, UNIQUE | 相册名 |
| description | TEXT | - | 描述 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

---

### album_photos（相册-照片关联表）- 预留

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| album_id | INTEGER | FK, PK | 相册 ID |
| photo_id | INTEGER | FK, PK | 照片 ID |
| added_at | DATETIME | DEFAULT NOW | 添加时间 |

---

## 数据库操作

### 常用查询示例

```python
from backend.database import SessionLocal, Photo, ImportHistory

# 创建会话
db = SessionLocal()

# 查询所有照片
photos = db.query(Photo).filter(Photo.file_type == 'photo').all()

# 按日期范围查询
from datetime import datetime
start = datetime(2024, 1, 1)
end = datetime(2024, 12, 31)
photos = db.query(Photo).filter(
    Photo.media_date >= start,
    Photo.media_date <= end
).all()

# 查询重复文件（相同 MD5）
from sqlalchemy import func
duplicates = db.query(Photo.md5_hash, func.count(Photo.id)).group_by(
    Photo.md5_hash
).having(func.count(Photo.id) > 1).all()

# 获取导入历史
history = db.query(ImportHistory).order_by(
    ImportHistory.start_time.desc()
).limit(10).all()

# 关闭会话
db.close()
```

### 设置操作

```python
from backend.database import get_setting, set_setting

# 获取设置
theme = get_setting('dark_mode', 'false')

# 设置值
set_setting('dark_mode', 'true')
```

---

## 数据库迁移

数据库初始化时会自动执行迁移：

1. **添加 total_size 列**：为旧的 import_history 表补加列
2. **移除 MD5 唯一约束**：允许相同 MD5 的 _dup 副本存在

---

## ER 图

```
┌─────────────┐     ┌─────────────┐
│   photos    │     │    tags     │
├─────────────┤     ├─────────────┤
│ id (PK)     │     │ id (PK)     │
│ filename    │     │ name        │
│ path (UQ)   │     │ created_at  │
│ size        │     └─────────────┘
│ md5_hash    │            │
│ media_date  │            │ M:N
│ file_type   │            │
│ ...         │     ┌─────────────┐
└─────────────┘     │ photo_tags  │
       │            ├─────────────┤
       │            │ photo_id(FK)│
       │ 1:N        │ tag_id (FK) │
       ▼            └─────────────┘
┌─────────────┐
│import_history│
├─────────────┤
│ id (PK)     │
│ source_path │
│ target_path │
│ status      │
│ ...         │
└─────────────┘
```
