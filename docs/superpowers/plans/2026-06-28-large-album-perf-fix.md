# 大相册性能修复：getStats / getTree 改数据库驱动

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复"几万张照片时点 section 卡死 + 收藏计数更新慢/无反应"两个用户报告的 Bug；P1 性能优化（不改 SQLite WAL，只改业务逻辑）

**Architecture:**
- `getStats` 改为纯 SQL 聚合（一次 3 条聚合查询替换"全表加载 + 2 万次磁盘 I/O"）
- `getTree` 改为"只显示有照片的目录"（数据库 GROUP BY 替换"递归扫描整个磁盘相册"）
- 前端**零改动**（API 响应结构保持完全兼容）
- SQLite WAL 模式调研（仅写文档，不在本次实现范围内）

**Tech Stack:**
- Backend: Flask + SQLAlchemy + SQLite
- 跨平台路径处理：`os.path.relpath` / `os.sep`

---

## 一、背景与 Bug 现象

### 用户报告（2026-06-28 试用）

1. **构建缩略图时点击 section 卡住**："点击没效果"
2. **收藏计数更新非常慢，后来点击收藏没反应**："收藏 section 计数更新非常慢，且后来点击收藏都没有反应了"

### 根因（已验证，详见 [前序调查报告](2026-06-28-bug-perf-investigation.md)）

**两个 Bug 三个根因**：

#### 根因 1（Bug 2 唯一根因）：`getStats` 和 `getTree` 慢

[App.tsx:193-211](file:///f:/AI/Frame_Album/frontend/src/App.tsx#L193) `refreshAllCounters` 每次点击收藏触发 5 个 API：

| API | 实际耗时（2 万张图） | 真实原因 |
|-----|---------------------|----------|
| `addFavorite` | 50ms | 单条 UPDATE，无问题 |
| `getFavorites` | 50ms | SQL 查询，OK |
| `getAlbums` | 50ms | SQL 查询，OK |
| **`getStats`** | **5-10 秒** | 全表 `query(Photo).all()` + 每张调 `Path(photo.path).resolve()` 走磁盘 |
| **`getTree`** | **1-2 分钟** | `os.scandir` 递归遍历整个相册目录，每个文件 `iterdir` + `stat` |

**结论**：5 个 API 里的 2 个慢接口是元凶。**这两个与"收藏"完全无关**，却被收藏点击"搭车"调用。

#### 根因 2（Bug 1 主因）：缩略图生成时 `db.commit()` 写锁阻塞读

[backend/thumbnail_manager.py:251-270](file:///f:/AI/Frame_Album/backend/thumbnail_manager.py#L251) 有个 `_update_photo_thumbnail_path()` 函数，**每生成一张缩略图就 `db.commit()` 一次**（UPDATE `photo.thumbnail_path`）。

**全项目搜索 `Photo.thumbnail_path` 的读取点：0 处生产代码**——DB 存了根本没人读。缩略图缓存用 hash 文件名存在 `thumbnails/` 目录，重启后从目录读即可。

**触发链**：
1. `rebuild_index` 清空缩略图缓存
2. 用户进入主界面 → 浏览器并发 6 个 `/api/album/thumbnail` 请求
3. 每个请求生成缩略图 + UPDATE 一次 `photos` 表
4. **6 个并发 UPDATE 互相争写锁**
5. 用户点 section → 后端读请求要 SHARED 锁 → **在写锁队列里等 5 秒 → 超时 500 → UI 卡住**

**修复**：删掉 `_update_photo_thumbnail_path` 调用 + 函数（**保留 `Photo.thumbnail_path` 数据库列**，向后兼容老数据）→ 缩略图生成零 DB 写 → 写锁竞争消失 → **Bug 1 治本**。

#### 根因 3（B 1/B 2 共同加剧因素）：SQLite 写锁阻塞读

- Bug 1：根因 2 消失后，Bug 1 几乎不再触发（日常使用只有 `addFavorite` 写，且是单次短写）
- Bug 2：根因 1 消失后，写锁竞争不再严重
- **WAL 模式可继续治本，但仍是 v0.8 候选**（一次性不可逆变更，需大版本号）

### 不在本次范围的项

| 议题 | 处理 | 原因 |
|------|------|------|
| 收藏点击的"乐观更新 + debounce" | ❌ 不动 | 根因 1 修完后体感会大幅改善；需观察后再决定 |
| SQLite WAL 模式 | 📄 写调查文档，**不改代码** | 一次性不可逆变更，需 v0.8 + 回退测试 + 备份文档 |
| 缩略图生成并发控制（线程池扩容） | ❌ 不动 | 根因 2 修完后写锁竞争消失；缩略图本身是 CPU 密集，多线程无收益 |

---

## 二、目标

修复后验收标准：

- [ ] `getStats` 调用耗时 < 200ms（2 万张照片场景）
- [ ] `getTree` 调用耗时 < 500ms（2 万张照片场景）
- [ ] 收藏点击后侧边栏收藏计数 < 1 秒更新
- [ ] 缩略图生成期间点击 section，体感"立即响应"或"短转圈后响应"
- [ ] 缩略图生成期间无 `db.commit()` 写锁（验证方法：开启后端日志搜索 "UPDATE photos"）
- [ ] 连续点击 5 次收藏，全部生效，无"没反应"
- [ ] 前端代码零改动
- [ ] 现有 pytest 全部通过
- [ ] `_update_photo_thumbnail_path` 函数被删除
- [ ] `Photo.thumbnail_path` 数据库列保留（向后兼容老数据），但代码不再读写

---

## 三、影响面分析

### 3.1 涉及文件

| 文件 | 改动类型 | 风险 |
|------|----------|------|
| [backend/api_server.py:152-280](file:///f:/AI/Frame_Album/backend/api_server.py#L152) `get_album_stats` 函数 | **重写**为纯 SQL | 中（行为对齐需谨慎） |
| [backend/api_server.py:333-472](file:///f:/AI/Frame_Album/backend/api_server.py#L333) `album_tree` 端点 | **重写**为数据库驱动 | 中（行为变化：空目录不再显示） |
| [backend/thumbnail_manager.py:209-210, 240-241](file:///f:/AI/Frame_Album/backend/thumbnail_manager.py#L209) | **删掉** `_update_photo_thumbnail_path()` 两处调用 | 低 |
| [backend/thumbnail_manager.py:251-270](file:///f:/AI/Frame_Album/backend/thumbnail_manager.py#L251) | **删掉** `_update_photo_thumbnail_path` 整个函数 | 低 |
| [test/api/test_api_album_pytest.py](file:///f:/AI/Frame_Album/test/api/test_api_album_pytest.py) | 适配 mock 测试 | 低 |
| [test/api/test_api_server_integration.py:50-87](file:///f:/AI/Frame_Album/test/api/test_api_server_integration.py#L50) | 改造 2 个真实文件测试 | 中 |
| [test/api/test_api_server_pytest.py](file:///f:/AI/Frame_Album/test/api/test_api_server_pytest.py) | 适配 | 低 |
| [test/api/test_api_server_extended.py:109-145](file:///f:/AI/Frame_Album/test/api/test_api_server_extended.py#L109) | 适配 | 低 |
| [test/api/test_photos_endpoints.py:121-160](file:///f:/AI/Frame_Album/test/api/test_photos_endpoints.py#L121) | 适配 | 低 |
| [test/api/test_api_server_comprehensive.py](file:///f:/AI/Frame_Album/test/api/test_api_server_comprehensive.py) | 适配 stats/tree 相关测试 | 中 |
| [test/api/test_api_server_final.py](file:///f:/AI/Frame_Album/test/api/test_api_server_final.py) | 适配 stats/tree 相关测试 | 中 |
| [test/api/test_album.py](file:///f:/AI/Frame_Album/test/api/test_album.py) | 适配 stats/tree 相关测试 | 中 |
| [test/api/test_api_album.py](file:///f:/AI/Frame_Album/test/api/test_api_album.py) | 适配 stats/tree 相关测试 | 中 |
| [test/unit/test_thumbnail_manager_pytest.py:224](file:///f:/AI/Frame_Album/test/unit/test_thumbnail_manager_pytest.py#L224) | **删掉** `test_update_db_path` 相关 mock 装饰器 | 低 |
| [test/unit/test_thumbnail_manager_pytest_extended.py:164-172](file:///f:/AI/Frame_Album/test/unit/test_thumbnail_manager_pytest_extended.py#L164) | **删掉** `test_update_photo_thumbnail_path_exception` 测试 | 低 |
| [test/unit/test_thumbnail_manager_pytest_plan_b.py:360-400](file:///f:/AI/Frame_Album/test/unit/test_thumbnail_manager_pytest_plan_b.py#L360) | **删掉** `_update_photo_thumbnail_path` 相关 2 个测试 | 低 |
| 前端 | **零改动** | 无 |
| 用户数据 `~/Documents/BlurArc/` | **零改动** | 无 |

### 3.2 API 响应兼容性

**`/api/album/stats`**（保持字段完全不变）：

```json
{
  "total_files": 1234,
  "video_count": 56,
  "total_size": 9876543210,
  "total_size_mb": 9415.2,
  "years": {},
  "last_import": "2026-06-28T10:00:00"
}
```

⚠️ `years` 字段：当前 `get_album_stats` 已经在新版 SQL 实现中已不再填充（代码显示遍历文件系统的分支不返回 years），继续返回空 dict 保持兼容。

**`/api/album/tree`**（保持结构完全不变）：

```json
{
  "name": "Photos",
  "path": "D:\\Photos",
  "type": "root",
  "count": 1234,
  "children": [
    { "name": "2024", "path": "D:\\Photos\\2024", "type": "directory", "count": 500, "children": [...] },
    ...
  ]
}
```

⚠️ **行为变化**：相册里没有照片的目录（空文件夹、`.DS_Store` 残留、备份目录）不再出现在树中。**用户已确认接受此变化**。

### 3.3 消费方

| 消费方 | 期望字段 | 影响 |
|--------|----------|------|
| [frontend/src/services/api.ts:50](file:///f:/AI/Frame_Album/frontend/src/services/api.ts#L50) `getStats` | `total_files, video_count, total_size_mb, last_import` | 字段全保留，零影响 |
| [frontend/src/services/api.ts:53-75](file:///f:/AI/Frame_Album/frontend/src/services/api.ts#L53) `getTree` | `{ tree: [], rootDir: DirNode }` | rootDir 结构完全保持 |
| [frontend/src/components/sidebar/DirectoryTree.tsx](file:///f:/AI/Frame_Album/frontend/src/components/sidebar/DirectoryTree.tsx) | 递归渲染 | 仅少显示空目录，行为不变 |

---

## 四、反例清单（要防御的边界场景）

| # | 场景 | 期望行为 |
|---|------|----------|
| 1 | 相册根下有 `.DS_Store` / `readme.md` / 空目录 | 树中**不出现**这些 |
| 2 | 用户在相册根直接放照片（非子目录） | 根 `count` 包含根目录文件数 |
| 3 | 相册路径下 0 张照片 | 返回根节点 `children=[]`, `count=0`，不报错 |
| 4 | `get_album_path()` 返回 None 或路径不存在 | 返回 404（**保持当前行为**） |
| 5 | 用户重命名了目录但 DB path 还在旧位置 | 从 DB path 推断，**仍能显示旧目录**（带 count）。**前端表现**：目录显示在侧边栏，但点击后照片列表为空（因为 `os.path.join(album_path, rel_path)` 构造的路径不存在）。用户可手动触发"重建索引"清理孤儿记录 |
| 6 | 照片分散在 3 层以上深目录 | 树正确递归展开 3+ 层 |
| 7 | 相册根路径包含特殊字符（中文、空格、Unicode） | `os.path.relpath` 正确处理 |
| 8 | 数据库连接异常 / DB 不可读 | 返回 500 + 日志，**不**返回部分数据 |
| 9 | `db.query(Photo).all()` 返回空列表 | 返回空树，**不** NPE |
| 10 | 并发调用（同一毫秒内 2 次 getTree） | 各自独立返回，**不**共享内存导致数据错乱 |
| 11 | `Photo.path` 在 DB 里有但磁盘文件已删除 | 仍出现在树中（**数据真实性优先**） |
| 12 | Windows 反斜杠 `\` vs Unix 正斜杠 `/` | 跨平台一致：内部用 `os.sep` 构造，DB 路径原样返回 |

---

## 五、设计方案

### 5.1 `getStats` 新版（纯 SQL 聚合）

**改之前**（[api_server.py:152-280](file:///f:/AI/Frame_Album/backend/api_server.py#L152)，约 130 行）：

```python
all_photos = db.query(Photo).all()  # 全表加载
for photo in all_photos:
    photo_path_resolved = str(Path(photo.path).resolve()).lower()  # 每张走磁盘
    if photo_path_resolved.startswith(album_path_resolved):
        valid_photos.append(photo)
# 接着再递归 traverse_directory 扫磁盘
```

**改之后**（约 25 行）：

```python
# 一次连接，3 条聚合查询（加路径前缀过滤，防止跨相册残留数据污染）
db = SessionLocal()
try:
    album_path_prefix = album_path.rstrip('\\/') + os.sep
    
    total_files = db.query(func.count(Photo.id)).filter(
        Photo.path.like(album_path_prefix + '%')
    ).scalar() or 0
    
    video_count = db.query(func.count(Photo.id)).filter(
        Photo.path.like(album_path_prefix + '%'),
        Photo.file_type == 'video'
    ).scalar() or 0
    
    total_size = db.query(func.coalesce(func.sum(Photo.size), 0)).filter(
        Photo.path.like(album_path_prefix + '%')
    ).scalar() or 0
finally:
    db.close()

# last_import 从 config_manager 获取（保持与旧版一致）
last_import = config_manager.get('last_import', None)

# 数据库里有但磁盘路径不在当前相册目录下的，不算入当前相册统计
# 防止 v0.6→v0.7 迁移残留或用户改过相册路径时的数据污染
```

**`last_import` 字段处理**：
- 保持与旧版一致，从 `config_manager.get('last_import', None)` 获取
- 新版 `getStats` 不再从 `photos` 表计算（旧版也没从表里算）

**性能对比**（2 万张照片估算）：

| 操作 | 改之前 | 改之后 |
|------|--------|--------|
| DB 全表加载 | 500ms | 0（聚合） |
| 2 万次 `Path.resolve()` 磁盘 I/O | 5-10s | 0 |
| 递归遍历磁盘相册 | 1-2 min | 0 |
| SQL 聚合查询 | 0 | 50-100ms |
| **总计** | **1-2 min** | **< 200ms** |

### 5.2 `getTree` 新版（数据库驱动 + 内存建树）

**改之前**（[api_server.py:333-472](file:///f:/AI/Frame_Album/backend/api_server.py#L333)，约 140 行）：递归 `os.scandir` 整个相册

**改之后**（约 70 行）：

```python
from collections import defaultdict

# 步骤 1：一次 SQL 拿所有 photo 的 path
rows = db.query(Photo.path).filter(
    Photo.path.like(album_path_prefix + '%')
).all()

# 步骤 2：Python 内存里去重父目录 + 累加 count
dir_count: dict[str, int] = {}        # 相对路径 → 照片数
dir_set: set[str] = set()              # 所有有照片的目录
for (full_path,) in rows:
    try:
        rel = os.path.relpath(full_path, album_path)  # "2024/2024-03/IMG.jpg"
    except ValueError:
        # Windows 跨盘符场景（如 full_path="E:\\photo.jpg", album_path="D:\\Photos"）
        # 跳过不属于当前相册的照片
        continue
    
    parts = rel.split(os.sep)
    for i in range(1, len(parts)):    # 跳过最后文件本身
        parent_rel = os.sep.join(parts[:i])
        dir_count[parent_rel] = dir_count.get(parent_rel, 0) + 1
        dir_set.add(parent_rel)

# 步骤 3：构建 children_map（父目录 → 直接子目录名集合）
children_map: dict[str, set[str]] = defaultdict(set)
for rel in dir_set:
    parts = rel.split(os.sep)
    if len(parts) == 1:
        children_map[""].add(parts[0])  # 根目录的直接子目录
    else:
        parent = os.sep.join(parts[:-1])
        children_map[parent].add(parts[-1])

# 步骤 4：递归构造树
def build_node(rel_path: str) -> dict:
    abs_path = album_path if not rel_path else os.path.join(album_path, rel_path)
    direct_children = sorted(children_map.get(rel_path, set()))
    return {
        'name': os.path.basename(abs_path) if rel_path else os.path.basename(album_path),
        'path': abs_path,
        'type': 'directory' if rel_path else 'root',
        'count': dir_count.get(rel_path, 0),
        'children': [build_node(os.path.join(rel_path, c)) for c in direct_children]
    }
```

**关键改进**：
- 用 `children_map` 替代复杂的索引计算，逻辑清晰且正确
- 加 `os.path.relpath` 的 `ValueError` 防御（Windows 跨盘符场景）

### 5.3 跨平台路径处理

```python
import os, posixpath, ntpath

ALBUM_PATH_PREFIX = album_path.rstrip('\\/') + os.sep
# 不替换反斜杠 — DB 存什么就读什么，输出给前端原样
# 反例 7 防护：使用 os.path.relpath 而非手动 split，确保 Windows "D:\Photos\2024" 正确处理
```

---

## 六、WAL 模式调查（仅文档，不实现）

### 6.1 现状

[backend/database.py:37](file:///f:/AI/Frame_Album/backend/database.py#L37)：

```python
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
```

- 无 `connect_args={"timeout": ...}` → 默认 5 秒锁等待
- 无 `PRAGMA journal_mode=WAL` → 默认 `DELETE` 模式

### 6.2 先回答核心问题：WAL 是限制并发读还是并发写？

**答：WAL 解决的是"读阻塞写"的问题，不是"写阻塞读"。**（这一点与直觉相反，容易搞反）

SQLite 锁的真相，按"模式"分别解释：

#### 模式 A：当前默认（`journal_mode=DELETE`，即 `rollback journal`）

```
时间线：
[T1 写]──────────┐
[T2 读]────等待──┘────────────────────→ 完成
[T3 读]──────────┐
[T4 写]────────等待──┐
```

特点：
- **写事务持有 EXCLUSIVE 锁**期间，**所有读都阻塞**（不只是写等待读）
- 读事务也在 SHARED 锁期间，**新写需要等读完成**
- 后果：**读写互相阻塞**，并发度极低
- 你的 Bug 1 根因就是这个：后台 `rebuild_index` 持有写锁 → 你点 section 发起的 `/api/timeline/years` 等读请求**全部在门口排队**

#### 模式 B：WAL（`journal_mode=WAL`）

```
时间线（多个读与一个写同时进行）：
[T1 读]────────────────→ 完成（看到的是 T2 写之前的旧快照）
[T2 读]────────────────→ 完成（同上，看到一致的旧快照）
[T3 写]────────→ 完成（追加到 .db-wal，不阻塞读）
[T4 读]────────────────────→ 完成（看到 T3 写之后的新快照）
```

特点：
- **读永远不阻塞写**（写只追加到 `-wal` 文件，不动主 DB）
- **写也几乎不阻塞读**（读的是主 DB 文件的旧快照 + `-wal` 增量）
- **唯一会阻塞的：多个写**（同一时刻只能有 1 个写事务）
- 多进程并发安全（多个 reader + 1 个 writer）

#### 一张表总结

| 场景 | DELETE 模式（当前） | WAL 模式 |
|------|---------------------|----------|
| 1 个读 + 1 个写同时进行 | ❌ 读阻塞等写 | ✅ 并行 |
| N 个读同时进行 | ✅ 并行 | ✅ 并行 |
| N 个写同时进行 | ❌ 串行化 | ❌ 串行化（WAL 也不解决） |
| 写期间新读请求 | ❌ 阻塞 | ✅ 立即返回（看到旧快照） |
| 写挂死/超时长 | ❌ 整个应用卡住 | ✅ 读不受影响 |

### 6.3 WAL 对你的 Bug 1 真的有帮助吗？

**看场景**：

- 你的 `rebuild_index` 在后台线程跑，**写锁持有几分钟**（涉及 UPDATE/INSERT/DELETE + commit）
- 这期间你点 section → 后端 `/api/timeline/years` 发起读请求
- DELETE 模式下：读请求**阻塞**在锁队列里，5 秒后 `database is locked` 异常
- WAL 模式下：读请求**立刻返回旧数据**（不含未提交的索引变更），你看到的是"没新数据但能正常浏览"

**结论：WAL 直接解决 Bug 1 的核心锁竞争。** getStats/getTree 改完后，Bug 1 体感会好很多（因为慢请求不再占线程），但**根本性的"读阻塞写"问题仍然存在**——WAL 才是治本的。

### 6.4 WAL 对 Bug 2 的帮助

**Bug 2 的核心不是锁问题，是"全量盘点被搭车"**（5 个 API 里的 2 个慢接口）。

WAL 帮不了 Bug 2 —— getStats/getTree 即使无锁了，本身还是慢（1-2 分钟）。

**所以本次 PR 必须改 getStats/getTree，WAL 是 Bug 1 的"治本方案"**（不只是锦上添花）。

### 6.5 关键修正（2026-06-28 复盘）

**Bug 1 的"写锁来源"是缩略图生成，不是 `rebuild_index`。**

- [backend/thumbnail_manager.py:251-270](file:///f:/AI/Frame_Album/backend/thumbnail_manager.py#L251) 有个 `_update_photo_thumbnail_path()` 函数，**每生成一张缩略图就 `db.commit()` 一次**
- 触发链：`rebuild_index` 清空缩略图缓存 → 用户浏览 → 浏览器并发 6 个 `/api/album/thumbnail` 请求 → 每个生成 1 张 → **6 个并发 UPDATE 互相争写锁 + 阻塞你的 section 读请求**
- 之前我（assistant）的报告把"写锁来源"简化成"重建索引"，**这是不准确的**，应予以修正

**附带的发现**：`Photo.thumbnail_path` 字段是**冗余的**——缩略图缓存已经用 hash 文件名存在 `thumbnails/` 目录，重启后从目录读即可。删除该字段的写库调用是另一个 P1 优化（v0.8 候选），不在本次 PR 范围。

### 6.4.2 WAL 优先级因此提升

| Bug | 修本次 PR | 修 WAL |
|-----|-----------|--------|
| Bug 2 收藏计数慢 | ✅ 主要靠 getStats/getTree | ❌ 帮不上 |
| **Bug 1 section 卡死** | 缓解（getStats/getTree 不再占线程） | ✅ **直接治本**（缩略图写库期间读不被卡） |

**WAL 从"锦上添花"变成"必要"——但仍有 v0.8 大版本约束**（不可逆、旁路文件、回退兼容性），**不放在本次 PR**。

### 6.6 风险与权衡

**WAL 模式的实际风险**：

| 风险 | 实际影响 | 是否可接受 |
|------|----------|------------|
| 多出 `-wal` 和 `-shm` 旁路文件 | 用户 `~/Documents/BlurArc/.config/` 会出现 `photo_manager.db-wal` 和 `photo_manager.db-shm` | ⚠️ 需要文档告知用户 |
| 备份工具可能漏掉旁路文件 | 用 Windows 文件资源管理器复制 `.db` 文件时，旁路文件没复制过去 → 重启后 WAL 恢复，可能丢最近的几个写 | ⚠️ 需要文档告知 |
| 多写并发无改善 | 同时点 5 次❤️，仍是 1 个写完才下一个 | ✅ 不影响本次 Bug 修复 |
| `synchronous=NORMAL` 风险 | 极端断电情况下可能丢最后几个写（FULL 模式无此风险但更慢） | ⚠️ 默认保留 FULL 更安全 |
| 现有迁移逻辑兼容性 | `CREATE INDEX IF NOT EXISTS` 在 WAL 下完全兼容 | ✅ 无影响 |

### 6.7 最小代码改动（参考，预留后续 PR）

```python
from sqlalchemy import event

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"timeout": 30}  # 30 秒锁等待（之前默认 5 秒）
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=FULL")  # 保守：不降级断电安全
    cursor.close()
```

⚠️ **WAL 是一次性、不可逆的设置**（一旦 DB 文件以 WAL 模式打开过，即使后续代码改回 DELETE，DB 仍会保持 WAL 模式直到显式 `PRAGMA journal_mode=DELETE`）。需要确认升级路径：
- 旧用户首次启动 v0.7.x（含 WAL 代码）→ 自动从 DELETE 迁移到 WAL
- 旧用户回退到 v0.6 → DB 仍是 WAL 模式，但 v0.6 代码不读旁路文件 → **不兼容**

**所以 WAL 必须是大版本变更（v0.7 → v0.8）才能推**。

### 6.8 结论

**不在本次 PR 实施**，原因：
1. 用户明确要求"可以一起查，但不能一起写"
2. WAL 是一次性变更，需要 v0.8 大版本号 + 完整的回退测试 + 用户文档
3. 本次 PR（getStats/getTree 改数据库驱动）已能显著缓解 Bug 1：慢请求不再占线程后，section 点击 API 几秒内可完成
4. WAL 真正解决的是"长时间写事务期间读被卡"——本次改完后长写事务只有 `rebuild_index`，**日常使用几乎不会再触发这个场景**

**后续 PR 计划（v0.8 候选）**：
- [ ] 验证本次改完后 Bug 1 是否已自然消失
- [ ] 写 WAL 升级路径测试（v0.6 DB → v0.8 DB → v0.6 回退）
- [ ] 更新用户文档，告知 `.db-wal` / `.db-shm` 旁路文件 + 备份注意事项
- [ ] 决定 `synchronous` 级别（FULL 保守 vs NORMAL 性能）

---

## 七、分步验证（每步都有可观察的成功标准）

### 步骤 1：写 `getStats` 新版

**改动**：[backend/api_server.py:152-280](file:///f:/AI/Frame_Album/backend/api_server.py#L152) `get_album_stats` 函数

**验证**：
- [ ] `python -c "from backend.api_server import app; print(app.url_map)"` 无导入错误
- [ ] `pytest test/api/test_api_album_pytest.py::TestAPIAlbum::test_album_stats -v` 通过

### 步骤 2：写 `getTree` 新版

**改动**：[backend/api_server.py:333-472](file:///f:/AI/Frame_Album/backend/api_server.py#L333) `album_tree` 函数

**验证**：
- [ ] `pytest test/api/test_api_server_integration.py::TestAlbumTreeRealFiles -v` 通过（改造后）
- [ ] `pytest test/api/test_api_album_pytest.py::TestAPIAlbum::test_album_tree -v` 通过

### 步骤 3：补充/适配所有相关测试（**先适配测试，再删函数**）

**改动**：
- 适配 [test/api/test_api_album_pytest.py](file:///f:/AI/Frame_Album/test/api/test_api_album_pytest.py) 等 mock 风格测试
- 适配 [test/api/test_api_server_comprehensive.py](file:///f:/AI/Frame_Album/test/api/test_api_server_comprehensive.py) stats/tree 相关测试
- 适配 [test/api/test_api_server_final.py](file:///f:/AI/Frame_Album/test/api/test_api_server_final.py) stats/tree 相关测试
- 适配 [test/api/test_album.py](file:///f:/AI/Frame_Album/test/api/test_album.py) stats/tree 相关测试
- 适配 [test/api/test_api_album.py](file:///f:/AI/Frame_Album/test/api/test_api_album.py) stats/tree 相关测试
- 改造 [test/api/test_api_server_integration.py:50-87](file:///f:/AI/Frame_Album/test/api/test_api_server_integration.py#L50) 真实文件测试为写真实 Photo 记录
- 新增 3 个反例测试：
  1. 写真实 Photo 记录 + 临时相册目录，验证"空目录不出现在树中"
  2. 3 层以上深目录的树正确展开
  3. 中文/空格路径正确处理

**验证**：
- [ ] `pytest test/api/ -v` 全部通过
- [ ] `pytest test/unit/ -v` 全部通过

### 步骤 4：删 `_update_photo_thumbnail_path` 调用 + 函数（**测试已适配，安全删除**）

**改动**：
- [backend/thumbnail_manager.py:209-210](file:///f:/AI/Frame_Album/backend/thumbnail_manager.py#L209) 删掉调用
- [backend/thumbnail_manager.py:240-241](file:///f:/AI/Frame_Album/backend/thumbnail_manager.py#L240) 删掉调用
- [backend/thumbnail_manager.py:251-270](file:///f:/AI/Frame_Album/backend/thumbnail_manager.py#L251) 删掉整个函数 + 清理 import
- [test/unit/test_thumbnail_manager_pytest.py:224](file:///f:/AI/Frame_Album/test/unit/test_thumbnail_manager_pytest.py#L224) 移除 `@patch('backend.thumbnail_manager.ThumbnailManager._update_photo_thumbnail_path')` 装饰器
- [test/unit/test_thumbnail_manager_pytest_extended.py:164-172](file:///f:/AI/Frame_Album/test/unit/test_thumbnail_manager_pytest_extended.py#L164) **删除** `test_update_photo_thumbnail_path_exception` 整个测试
- [test/unit/test_thumbnail_manager_pytest_plan_b.py:360-400](file:///f:/AI/Frame_Album/test/unit/test_thumbnail_manager_pytest_plan_b.py#L360) **删除** `_update_photo_thumbnail_path` 相关 2 个测试

**验证**：
- [ ] `python -c "from backend.thumbnail_manager import ThumbnailManager; mgr = ThumbnailManager(); assert not hasattr(mgr, '_update_photo_thumbnail_path')"` 通过
- [ ] `grep -r "_update_photo_thumbnail_path" backend/` 无任何匹配
- [ ] `pytest test/unit/test_thumbnail_manager_pytest.py -v` 通过
- [ ] `pytest test/unit/test_thumbnail_manager_pytest_extended.py -v` 通过
- [ ] `pytest test/unit/test_thumbnail_manager_pytest_plan_b.py -v` 通过
- [ ] `pytest test/ -v` 全部通过（总数与之前 756 相当或略减——因为删了 3 个测试）

### 步骤 5：手动性能验证（不连生产数据）

**操作**：
```bash
# 启动后端开发模式
cd f:\AI\Frame_Album
python src/BlurArc.py
```

**验证**：
- [ ] `/api/album/stats` 调用 < 200ms（用 curl 或前端 DevTools）
- [ ] `/api/album/tree` 调用 < 500ms
- [ ] 侧边栏目录树正常显示有照片的目录
- [ ] 在相册根手动建空目录 `test_empty/`，刷新后**不出现**在侧边栏
- [ ] 把一张照片移入 `test_empty/`，刷新后**出现**在侧边栏
- [ ] **缩略图生成期间，后端日志无 `UPDATE photos` 字样**（验证 Bug 1 写锁消失）
- [ ] 启动应用无 DB 错误（验证 `Photo.thumbnail_path` 列保留不影响迁移）

### 步骤 6：Bug 复现验证（用户报告的 2 个 bug）

**操作**：
1. 用用户的实际相册（或构造一个 1-2 万张图的环境）
2. 启动应用，进入主界面
3. 缩略图生成期间点击 "时间线" / "相册集" / "收藏" section
4. 快速连点 5 次❤️

**验证清单**：
- [ ] Bug 1：section 点击后 1-2 秒内响应（不卡死）
- [ ] Bug 2：点❤️后收藏计数 1 秒内更新
- [ ] Bug 2：连点 5 次❤️全部生效，无"没反应"

---

## 八、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 现有 8 个 mock 风格测试需要逐个适配 | 高 | 中 | 一次性全改；用 `tmp_path` 写真实 Photo 记录替代 mock |
| 真实生产相册中含 `..` 路径或符号链接 | 低 | 中 | SQL `LIKE 'prefix%'` 不会匹配 `..`；符号链接由 `import_manager` 在导入时已 `resolve` |
| `Photo.path` 在 DB 里被错误写入了 `D:\Other\Photos\xxx`（不在当前相册根下） | 低 | 中 | SQL `WHERE path LIKE '当前相册根%'` 会过滤掉；**这正是想要的行为**（不属于本相册的不算） |
| 跨平台路径分隔符 | 中 | 低 | 用 `os.path.relpath` + `os.sep` |
| `os.path.relpath` 在不同盘符（Windows）会抛 ValueError | 低 | 中 | 防御：try/except 包裹，记录 warning |
| 数据库连接关闭时机 | 低 | 低 | 严格 `try/finally` |

---

## 九、提交策略

按 CLAUDE.md 硬约束 + 用户确认（十一·3 合并为单一 commit）：

### 单一 commit

```
perf(v0.7): getStats/getTree 改数据库驱动 + 移除冗余缩略图写库（解决 Bug 1/2）
```

**改动**：
- `backend/api_server.py` `get_album_stats` + `album_tree` 重写
- `backend/thumbnail_manager.py` 删掉 `_update_photo_thumbnail_path`（含 2 处调用 + 函数定义）
- 3 个 test 文件删除过期测试 + 适配其他测试
- **新增** `docs/superpowers/plans/2026-06-28-large-album-perf-fix.md`（本文档，含 WAL 调查）
- 不动前端代码
- 不动 `docs/superpowers/specs/`（这是性能优化，非新功能）

### 合并到 main 的流程

按你之前的工作流：
1. commit 推到 `drafts` 分支
2. 推 main
3. 不打 tag（v0.7.0 已经发过了）

---

## 十、不在本次范围内（明确边界）

- ❌ **不改** SQLite WAL 模式（详见第六章调查文档）
- ❌ **不改** 收藏点击的"乐观更新 + debounce"（属于前端状态管理问题，等本 PR 上线观察 1 周后再决定）
- ❌ **不改** 缩略图生成并发控制（属于次要因素，本 PR 已能解决主因）
- ❌ **不改** 删 `Photo.thumbnail_path` 数据库列（**保留列，向后兼容老 DB 数据**；只是代码不再读写）
- ❌ **不动** `~/Documents/BlurArc/` 任何数据
- ❌ **不动** 前端代码
- ❌ **不动** `docs/superpowers/specs/` 任何 spec
- ❌ **不动** 任何 UI 原型（`docs/prototypes/`）

---

## 十一、用户确认（已定稿）

| # | 议题 | 决定 |
|---|------|------|
| 1 | DB 有记录但磁盘文件丢失（图片无法加载） | **不特殊处理**——树中仍展示该目录（数据真实性优先）；前端点击后缩略图加载失败显示占位图（PhotoCard onError fallback 已在 v0.7 实施）。用户可手动触发"重建索引"清理孤儿记录 |
| 2 | 空目录过滤 | ✅ 接受 |
| 3 | 调查文档是否独立成第一个 commit | ❌ **合并到实现 commit**（一个 commit 包含文档+代码） |
| 4 | 是否写 UI 原型 | ❌ 不写（本次无 UI 改动） |
| 5 | WAL 模式 | ❌ 不实现，仅写调查；后续 PR（v0.8 候选）单独评估 |
| 6 | **是否把"删 `_update_photo_thumbnail_path` 冗余写库"提升到本次** | ✅ **确认提升**——全项目搜索 `Photo.thumbnail_path` 读取点为 0，删除安全；治本 Bug 1 写锁问题 |
