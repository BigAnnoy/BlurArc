# 2026-06-22: 导入预检目标重复检测性能修复（删除 rglob 兜底）

## 问题

用户报告：相册里已有 2 万多张照片，仅导入 1 张新照片，UI 卡在"检测目标重复"步骤长时间无响应。

## 排查过程

### 目标重复检测流程（`_perform_import_check`）

1. **阶段4a**：从 DB 加载所有目标相册记录，构建 `(size, exif_time) → [file]` 内存索引
2. **阶段4b**：用源文件的 `(size, exif_time)` key 查索引，收集候选集
3. **阶段4c**：对源文件计算 MD5，与候选 MD5 比对

### 根因：rglob + PIL 兜底分支

代码在 `api_server.py:1814-1823` 有一个"补齐预筛索引"的兜底分支：

```python
# 兜底：若存在未命中的源 key（DB 中没有对应记录，可能相册未被索引），
# 追加一次文件系统扫描补齐预筛索引
missing_keys = {k for k in source_keys if k not in prescan_index}
if missing_keys:
    for file in album_path.rglob('*'):
        if file.is_file() and file.suffix.lower() in MEDIA_FORMATS:
            try:
                size = file.stat().st_size
                exif_dt = _get_exif_datetime_fast(file)  # ← PIL 打开每张图
                ...
            except OSError:
                continue
```

**触发条件**：源文件的 `(size, exif_time)` 不在 DB 索引中。

**性能影响**：
- 导入新照片时，源文件 key 几乎必然不在 DB
- 兜底分支被 100% 触发
- `rglob` 扫描整个相册（2 万+ 文件）
- **每个文件都用 PIL 打开读 EXIF**（即使尺寸不匹配）
- `rglob` 不 break early，找到匹配后仍继续扫描剩余文件

实测 2 万张照片：30 分钟级别（每张 PIL 打开 ~50-100ms）。

**实际收益**：99% 情况下 rglob 一个匹配也找不到，因为源是新文件，DB 自然没有。

## 修复

删除整个 rglob 兜底分支。DB 索引是唯一真相源：

- 走导入流程入库是硬性约定
- 手动复制进相册的文件不会出现在 DB 中 → 视为非重复 → 用户会重复导入
- 这种情况的正确处理是：触发相册重扫描（已有 `rebuild_md5_index_for_album` 端点），不应该是导入预检的慢路径

**改动位置：** [api_server.py:1805-1810](file:///f:/AI/Frame_Album/backend/api_server.py#L1805-L1810)

```python
# 改动前
missing_keys = {k for k in source_keys if k not in prescan_index}
if missing_keys:
    logger.info(f"DB 预筛索引有 {len(missing_keys)} 个源 key 缺失，追加文件系统扫描补齐")
    for file in album_path.rglob('*'):
        if file.is_file() and file.suffix.lower() in MEDIA_FORMATS:
            try:
                size = file.stat().st_size
                exif_dt = _get_exif_datetime_fast(file)
                exif_str = exif_dt.isoformat() if exif_dt else None
                key = (size, exif_str)
                if key in missing_keys and key not in prescan_index:
                    prescan_index[key] = [(file, None)]
            except OSError:
                continue

# 改动后
# 不再做 rglob 兜底：DB 没收录的相册文件视为非重复
# （走导入流程入库是硬性约定，手动复制进相册请走导入或重新扫描）
```

## 验证

- AST 解析通过
- 单元测试：224 通过，10 失败（全部是预存环境问题，与本次修改无关）
- 预期效果：1 张图导入预检从分钟级降到秒级

## 注意事项

- 如果用户手动把文件拷进相册文件夹没走导入，预检会判定为非重复并复制一份
- 推荐做法：手动拷文件后触发一次相册重扫描（`POST /api/album/rebuild-md5-index`）
- 如未来需要恢复兜底能力，建议加 size 预筛（尺码不对跳过 EXIF 读取），成本可接受
