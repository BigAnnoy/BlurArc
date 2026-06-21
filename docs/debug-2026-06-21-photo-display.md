# 手机端照片显示问题 — 诊断报告

> 日期: 2026-06-21 | 状态: 根因已确认

---

## 现象

1. 相册 Tab 只显示 2 张照片，PC 端实际有 6 张
2. 缩略图和预览大图加载失败（403）
3. 可以显示文件名和时间信息

---

## 根因

### 根因 1：sections 端点查数据库，数据库记录不完整

`/api/mobile/photos/sections` 查询 `Photo` 数据库表：

```python
Photo.query.filter_by(media_date=...).all()
```

数据库当前只有 **2 条记录**，且都指向临时目录：

| filename | path | 在相册目录下? |
|----------|------|--------------|
| 20260618_215207_001.jpg | `%TEMP%\tmpv9gwftoe\target\2026-06\...` | ❌ |
| 20260618_215207_001.jpg | `%TEMP%\tmpazrgiinc\target\2026-06\...` | ❌ |

但文件系统 `C:\Users\BIGANNOY\Pictures\2026-06\` 实际有 **6 张照片**。

**原因：** 测试时导入到临时目录，数据库记录在此。后来使用 `changeAlbumPath` 更改了相册路径，但数据库没有重建索引。照片在磁盘上但数据库里没有。

### 根因 2：数据库路径在相册目录外 → 后端路径校验 403

后端 `/api/mobile/thumbnail` 做了目录权限校验：

```python
if not Path(path).resolve().is_relative_to(Path(album_path).resolve()):
    return jsonify({"error": "路径不在相册目录下"}), 403
```

数据库中的路径是 `%TEMP%\...`，不在 `C:\Users\BIGANNOY\Pictures` 下，所以全部 403。

**验证结果：**

| 请求类型 | 路径 | 结果 |
|---------|------|------|
| thumbnail via temp path | `%TEMP%\tmpv9...` | 403 ❌ |
| thumbnail via album path | `C:\Users\...\Pictures\...` | 200 ✅ (6972 bytes) |
| preview via album path | `C:\Users\...\Pictures\...` | 200 ✅ (2MB) |

---

## 修复方案

### 方案 A（推荐）：重建数据库索引

在 PC 端 Blur Arc 设置中点击「重建索引」，让数据库重新扫描相册目录。这是最正确的修复，不会破坏数据一致性。

**操作步骤：**
1. 打开 Blur Arc → ⚙️ 设置 → 重建索引
2. 等待重建完成
3. 刷新手机端页面

### 方案 B：修改 sections 端点，回退到文件系统扫描

如果数据库为空或记录不足，fallback 到 `/api/mobile/photos` 逻辑去扫描文件系统。但可能返回重复数据或缺少 `media_date`。

### 方案 C：增加 `/api/system/rebuild_index` 的自动调用

在检测到数据库记录与文件系统不同步时自动触发重建。

---

## 关联问题

- `_PhotoGridItem` 使用 `Image.network` 而非 `CachedNetworkImage`，加载失败时没有重试
- sections 端点返回的 `thumbnail` URL 不含 token（但 Flutter 端没使用这个 URL，而是用 `api.getThumbnailUrl(photo.path)` 手动构造，这个问题不存在）
- 当前测试 token 名称为 "Manual"，配对的 token 名称为 "BlurArc Mobile"

## 建议修复优先级

1. **推荐用户重建索引**（最快修复，5 秒）
2. **长期：** 给 sections 端点加 filesystem fallback
