-- 2026_06_23_add_photo_path_unique.sql
-- Plan B - Optimization 3 prerequisite
-- 为 Photo.path 加命名 UNIQUE 索引，支持 INSERT OR IGNORE
-- 注意：Photo.path 在 ORM 中已用 unique=True 隐式创建唯一索引
--       （SQLite 自动命名为 sqlite_autoindex_photos_<n>）
--       本迁移额外创建一个命名索引 idx_photo_path_unique 便于引用和监控
--       IF NOT EXISTS 保证幂等
--
-- 注意：先清理重复（理论上不应有重复，但防御性处理）
--       生产环境应该先做一致性检查再执行删除

DELETE FROM photos
WHERE id NOT IN (
    SELECT MIN(id) FROM photos GROUP BY path
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_photo_path_unique ON photos(path);
