# v0.7 性能审计报告

**日期**：2026-06-29
**类型**：性能优化
**状态**：待实施

---

## 审计范围

| 模块 | 文件 | 状态 |
|------|------|------|
| 后端 API | `backend/api_server.py`（3800+ 行） | ✅ 已审计 |
| 数据模型 | `backend/database.py` | ✅ 已审计 |
| 缩略图 | `backend/thumbnail_manager.py` | ✅ 已审计 |
| 导入管理 | `backend/import_manager.py` | ✅ 已审计 |
| 前端状态 | `frontend/src/App.tsx` | ✅ 已审计 |
| 时间线 | `frontend/src/components/timeline/TimelineView.tsx` | ✅ 已审计 |

---

## P0：N+1 查询（确认 3 处）

### #1 `get_albums()` — 每个相册 2 次额外查询

**文件**：[backend/api_server.py](../../backend/api_server.py#L2593-L2620) 第 2593-2620 行

**问题代码**：
```python
albums = db.query(Album).all()  # 1 次查询
for album in albums:
    if album.cover_photo_id:
        cover_photo = db.query(Photo).filter(...).first()  # N 次查询！
    photo_count = _album_photo_count(db, album.id)  # 又是 N 次查询！
```

**影响**：10 个相册 = 1 + 10 + 10 = **21 次数据库查询**

**验证**：✅ 确认，循环内两次独立查询

#### 修复方案

用一次 `JOIN` + `GROUP BY` 聚合替代循环内查询：

```python
from sqlalchemy import func

albums = db.query(
    Album,
    Photo.path.label('cover_path'),
    func.count(AlbumPhoto.photo_id).label('photo_count')
).outerjoin(Photo, Album.cover_photo_id == Photo.id
).outerjoin(AlbumPhoto, Album.id == AlbumPhoto.album_id
).group_by(Album.id).all()

result = []
for album, cover_path, count in albums:
    result.append({
        'id': album.id,
        'name': album.name,
        'cover_photo_id': album.cover_photo_id,
        'cover_path': cover_path,
        'photo_count': count,
        'created_at': album.created_at.isoformat() if album.created_at else None,
        'description': album.description,
    })
```

**关键细节**：
- 用 `outerjoin` 而非 `join`，确保空相册也返回
- `func.count(AlbumPhoto.photo_id)` 统计关联照片数
- `Photo.path` 作为封面路径直接返回，无需额外查询
- 删除 `_album_photo_count()` 在此处的调用

**涉及文件**：
- `backend/api_server.py` — 修改 `get_albums()` 函数

#### 测试

1. **单元测试**：
   - 创建 3 个相册，分别有 0、5、10 张照片
   - 调用 `GET /api/albums`，验证返回 `photo_count` 分别为 0、5、10
   - 验证空相册的 `cover_path` 为 `null`

2. **集成测试**：
   - 启动应用，导入 20 张照片到不同相册
   - 调用 API，验证每个相册的 `photo_count` 与实际一致

3. **回归测试**：
   - 验证前端相册列表页正常渲染（封面图 + 计数）

#### 验收标准

- [ ] `GET /api/albums` 只执行 **1 次 SQL 查询**（通过 `echo=True` 或日志验证）
- [ ] 返回的 `photo_count` 与实际照片数一致
- [ ] 空相册 `photo_count` 为 0，不报错
- [ ] 无封面照片的相册 `cover_path` 为 `null`
- [ ] 前端相册列表页正常显示封面和计数

---

### #2 `get_timeline_years()` — 每年 1 次额外查询

**文件**：[backend/api_server.py](../../backend/api_server.py#L3155-L3161) 第 3155-3161 行

**问题代码**：
```python
for year_data in years_data:
    cover_photos = db.query(Photo).filter(
        extract('year', Photo.media_date) == year,
        Photo.file_type == 'photo'
    ).order_by(Photo.media_date).limit(4).all()  # N 次查询！
```

**影响**：5 个年份 = 5 次额外查询（每次 LIMIT 4 但仍是独立 SQL）

**验证**：✅ 确认

#### 修复方案

用窗口函数一次拿完所有年份的封面图（SQLite 3.25+ 支持）：

```python
from sqlalchemy import func

# 步骤 1：一次查询获取所有年份的前 4 张封面
subq = db.query(
    Photo.id,
    Photo.path,
    Photo.media_date,
    func.row_number().over(
        partition_by=func.strftime('%Y', Photo.media_date),
        order_by=Photo.media_date
    ).label('rn')
).filter(Photo.file_type == 'photo').subquery()

covers = db.query(subq).filter(subq.c.rn <= 4).all()

# 步骤 2：在 Python 中按年份分组
covers_by_year = {}
for row in covers:
    year = row.media_date.strftime('%Y')
    covers_by_year.setdefault(year, []).append({
        'id': row.id,
        'path': row.path,
        'media_date': row.media_date.isoformat() if row.media_date else None,
    })

# 步骤 3：构建返回结果
result = []
for year_data in years_data:
    year = str(year_data[0])
    result.append({
        'year': year,
        'count': year_data[1],
        'cover_photos': covers_by_year.get(year, []),
    })
```

**关键细节**：
- `func.strftime('%Y', Photo.media_date)` 是 SQLite 语法，兼容性好
- `row_number()` 窗口函数按年份分区，每个分区内按日期排序取前 4
- Python 端分组是 O(n) 操作，n = 年份数 × 4，开销极小

**涉及文件**：
- `backend/api_server.py` — 修改 `get_timeline_years()` 函数

#### 测试

1. **单元测试**：
   - 创建 2019-2024 共 6 个年份的照片数据
   - 调用 `GET /api/timeline/years`
   - 验证每个年份返回最多 4 张封面
   - 验证封面按日期升序排列

2. **边界测试**：
   - 某年份只有 1-2 张照片，验证封面数正确
   - 某年份没有照片，验证 `cover_photos` 为空数组

3. **回归测试**：
   - 前端时间线年视图正常渲染封面缩略图

#### 验收标准

- [ ] `GET /api/timeline/years` 只执行 **1 次 SQL 查询**获取封面（年份统计查询另计）
- [ ] 每个年份最多返回 4 张封面
- [ ] 封面按日期升序排列
- [ ] 照片不足的年份封面数 < 4，不报错
- [ ] 前端时间线年视图正常显示

---

### #3 `get_timeline_months()` — 同上

**文件**：[backend/api_server.py](../../backend/api_server.py#L3251-L3257) 第 3251-3257 行

**问题代码**：与 #2 完全相同的 N+1 模式

**验证**：✅ 确认

#### 修复方案

与 #2 相同模式，分区键改为 `strftime('%Y-%m', media_date)`：

```python
from sqlalchemy import func

# 步骤 1：一次查询获取所有月份的前 4 张封面
subq = db.query(
    Photo.id,
    Photo.path,
    Photo.media_date,
    func.row_number().over(
        partition_by=func.strftime('%Y-%m', Photo.media_date),
        order_by=Photo.media_date
    ).label('rn')
).filter(Photo.file_type == 'photo').subquery()

covers = db.query(subq).filter(subq.c.rn <= 4).all()

# 步骤 2：在 Python 中按月份分组
covers_by_month = {}
for row in covers:
    month_key = row.media_date.strftime('%Y-%m')
    covers_by_month.setdefault(month_key, []).append({
        'id': row.id,
        'path': row.path,
        'media_date': row.media_date.isoformat() if row.media_date else None,
    })

# 步骤 3：构建返回结果
result = []
for month_data in months_data:
    month_key = month_data[0]  # 'YYYY-MM'
    result.append({
        'month': month_key,
        'count': month_data[1],
        'cover_photos': covers_by_month.get(month_key, []),
    })
```

**涉及文件**：
- `backend/api_server.py` — 修改 `get_timeline_months()` 函数

#### 测试

1. **单元测试**：
   - 创建跨 12 个月的照片数据
   - 调用 `GET /api/timeline/months`
   - 验证每个月返回最多 4 张封面
   - 验证封面按日期升序排列

2. **边界测试**：
   - 某月只有 1 张照片，验证封面数正确
   - 某月没有照片，验证 `cover_photos` 为空数组

3. **回归测试**：
   - 前端时间线月视图正常渲染封面缩略图

#### 验收标准

- [ ] `GET /api/timeline/months` 只执行 **1 次 SQL 查询**获取封面
- [ ] 每个月最多返回 4 张封面
- [ ] 封面按日期升序排列
- [ ] 前端时间线月视图正常显示

---

## P1：索引缺失

### #4 `favorited_at` 索引 — 迁移脚本有但 init_db 未执行

**文件**：
- 迁移脚本：[backend/migrations/2026_06_25_add_v0.7_fields.sql](../../backend/migrations/2026_06_25_add_v0.7_fields.sql#L8) 第 8 行
- 数据库模型：[backend/database.py](../../backend/database.py#L224-L272) `init_db()` 函数

**问题**：
- 迁移脚本中有 `CREATE INDEX IF NOT EXISTS ix_photos_favorited_at ON photos (favorited_at)`
- 但 `database.py` 的 `init_db()` 中 v0.7 迁移部分（第 224-272 行）只添加了字段，没有创建索引
- 新用户首次运行时索引不会自动创建

**影响**：收藏数量大时 `ORDER BY favorited_at` 全表扫描

**验证**：✅ 确认，`init_db()` 只创建了 `media_date` 和 `path` 的索引

#### 修复方案

在 `init_db()` 的 v0.7 迁移区块末尾添加索引创建逻辑：

```python
# 在 init_db() 中，v0.7 字段迁移之后添加：

# 为 favorited_at 创建索引（收藏视图排序需要）
try:
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_photos_favorited_at ON photos (favorited_at)"
            )
        )
        conn.commit()
except Exception:
    pass  # 表尚未创建时忽略
```

**插入位置**：[database.py](../../backend/database.py#L272) 第 272 行（v0.7 字段迁移 `try` 块结束后）

**涉及文件**：
- `backend/database.py` — 修改 `init_db()` 函数

#### 测试

1. **单元测试**：
   - 新建一个空数据库，调用 `init_db()`
   - 执行 `PRAGMA index_list(photos)`，验证 `ix_photos_favorited_at` 存在

2. **迁移测试**：
   - 用旧版数据库（无 `favorited_at` 列）运行 `init_db()`
   - 验证字段和索引都被正确创建

3. **性能验证**：
   - 插入 10K 条收藏记录
   - 执行 `EXPLAIN QUERY PLAN SELECT * FROM photos WHERE is_favorite=1 ORDER BY favorited_at`
   - 验证使用了 `ix_photos_favorited_at` 索引

#### 验收标准

- [ ] 新数据库初始化后，`ix_photos_favorited_at` 索引存在
- [ ] 旧数据库升级后，索引被自动补建
- [ ] `EXPLAIN QUERY PLAN` 显示收藏排序使用索引
- [ ] 重复调用 `init_db()` 不报错（幂等）

---

## P1：路径不一致

### #5 缩略图缓存使用旧路径

**文件**：[backend/thumbnail_manager.py](../../backend/thumbnail_manager.py#L36) 第 36 行

**问题代码**：
```python
self.cache_dir = Path('~/.photomanager/thumbnails').expanduser()
```

**验证**：✅ 确认，v0.7 规范是 `~/Documents/BlurArc/thumbnails/`

**影响**：
- 升级后旧缩略图不会被复用
- 数据分散在两个目录
- 卸载时可能遗漏

#### 修复方案

使用统一的 `_get_user_data_dir()` 函数：

```python
from .config_manager import _get_user_data_dir

class ThumbnailManager:
    def __init__(self):
        # v0.7: 统一数据目录
        self.cache_dir = _get_user_data_dir() / 'thumbnails'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        ...
```

**关键细节**：
- `_get_user_data_dir()` 已在 `config_manager.py` 中定义
- 需要处理循环导入（`thumbnail_manager.py` 可能被 `config_manager.py` 间接导入）
- 如果循环导入存在，改用延迟导入或直接计算路径

**涉及文件**：
- `backend/thumbnail_manager.py` — 修改 `ThumbnailManager.__init__()`

#### 测试

1. **单元测试**：
   - 创建 `ThumbnailManager` 实例
   - 验证 `cache_dir` 路径包含 `Documents/BlurArc/thumbnails`

2. **集成测试**：
   - 启动应用，生成一张缩略图
   - 验证缩略图文件出现在 `~/Documents/BlurArc/thumbnails/` 下

3. **迁移测试**（可选）：
   - 检查旧路径 `~/.photomanager/thumbnails/` 是否存在
   - 如存在，提示用户可手动迁移或删除

#### 验收标准

- [ ] `ThumbnailManager.cache_dir` 指向 `~/Documents/BlurArc/thumbnails/`
- [ ] 缩略图生成后文件出现在正确目录
- [ ] 应用启动不报循环导入错误
- [ ] 旧路径的缩略图不影响新功能（只是不复用）

---

## P2：冗余查询

### #6 `album_stats` 路由重复查询 `last_import`

**文件**：[backend/api_server.py](../../backend/api_server.py#L186-L238)

**问题**：
- `get_album_stats()` 内部第 188 行查了 `config.get_last_import()`
- `album_stats()` 路由第 237 行又查了一次 `config.get_last_import()`

**验证**：✅ 确认，两次独立调用

**影响**：每次加载统计多读一次配置文件（轻微，文件 I/O 约 1-2ms）

#### 修复方案

删除路由中的重复调用，直接使用 `get_album_stats()` 返回的结果：

```python
@app.route('/api/album/stats', methods=['GET'])
def album_stats():
    """获取相册统计信息"""
    try:
        config = get_config()
        stats = get_album_stats()  # 已包含 last_import
        
        return jsonify({
            'success': True,
            'data': stats,
        })
    except Exception as e:
        logger.error(f"获取相册统计失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
        }), 500
```

**改动**：删除第 235-240 行的重复 `config.get_last_import()` 调用

**涉及文件**：
- `backend/api_server.py` — 修改 `album_stats()` 路由

#### 测试

1. **单元测试**：
   - 调用 `GET /api/album/stats`
   - 验证返回的 `last_import` 字段存在且格式正确

2. **性能验证**：
   - 在 `config.get_last_import()` 中加日志
   - 调用 API，验证只被调用 1 次

#### 验收标准

- [ ] `GET /api/album/stats` 返回的 `last_import` 与之前一致
- [ ] `config.get_last_import()` 只被调用 1 次
- [ ] 前端相册统计页正常显示

---

### #7 `_album_photo_count` 被 5 处独立调用

**文件**：[backend/api_server.py](../../backend/api_server.py#L134-L137)

**调用位置**：
| 行号 | 函数 | 场景 |
|------|------|------|
| 2613 | `get_albums()` | 相册列表 |
| 2680 | `get_album()` | 单个相册详情 |
| 2727 | `update_album()` | 更新相册后返回 |
| 2840 | `merge_albums()` | 合并相册后返回 |
| 3005 | `duplicate_album()` | 复制相册后返回 |

**验证**：✅ 确认，每次都是独立的 `SELECT COUNT(*)` 查询

**影响**：每次相册操作多 1 次 COUNT 查询。在 `get_albums()` 中已归入 #1 N+1 问题

#### 修复方案

**#1 修复后**，`get_albums()` 中的 N 次调用自动消失。

其余 4 处（`get_album`、`update_album`、`merge_albums`、`duplicate_album`）都是单次操作，无法合并优化，**暂不处理**。

#### 验收标准

- [ ] #1 修复后，`get_albums()` 不再调用 `_album_photo_count()`
- [ ] 其余 4 处调用保持不变，功能正常

---

## P3：可优化但影响小

### #8 `album_tree()` Python 端字符串操作

**文件**：[backend/api_server.py](../../backend/api_server.py#L278-L299)

**问题**：对每张照片路径做 `os.path.relpath()` + `split()` + 循环构造所有父目录。20K 照片时 ~10K 目录，Python 端字符串操作约 50-100ms。

**验证**：✅ 确认存在，但实际影响不大（一次查询 + 内存计算，无额外 I/O）

**评估**：暂不优化，当前实现已足够高效

---

### #9 `_escape_like` 重复定义

**验证**：❌ 已修正，只定义了一处（之前审计有误）

---

### #10 前端状态冗余

**文件**：[frontend/src/App.tsx](../../frontend/src/App.tsx#L22-L40)

**问题**：同时维护 `photos`、`totalPhotos`、`currentPage`、`hasMore` 等多个独立 state

**验证**：✅ 确认存在，但 React 18 对多 state 合并优化较好，实际渲染影响小

**评估**：暂不优化，可用 Zustand/Context 统一管理但引入新依赖不值得

---

## 修复优先级与实施计划

| 优先级 | 问题 | 修复方案 | 测试 | 验收标准 |
|--------|------|----------|------|----------|
| **P0** | #1 `get_albums()` N+1 | JOIN + GROUP BY 聚合 | 单元测试 + 前端回归 | 1 次查询，计数正确 |
| **P0** | #2 timeline years N+1 | 窗口函数一次查询 | 单元测试 + 前端回归 | 1 次查询，封面正确 |
| **P0** | #3 timeline months N+1 | 窗口函数一次查询 | 单元测试 + 前端回归 | 1 次查询，封面正确 |
| **P1** | #4 `favorited_at` 索引 | `init_db()` 加索引创建 | 索引存在性 + EXPLAIN | 索引存在，排序走索引 |
| **P1** | #5 缩略图旧路径 | 改用 `_get_user_data_dir()` | 路径验证 + 生成测试 | 文件出现在正确目录 |
| **P2** | #6 stats 重复查询 | 删除重复调用 | API 返回验证 | last_import 只查 1 次 |

---

## 备注

- N+1 查询是**最严重**的性能问题，在相册/时间线视图频繁触发
- 索引缺失在数据量 < 50K 时影响不明显，但会随数据增长恶化
- 缩略图路径问题不影响功能，但违反 v0.7 数据目录统一规范
- #7 中 `_album_photo_count` 的 4 处单次调用无需优化，属于合理的单次查询
