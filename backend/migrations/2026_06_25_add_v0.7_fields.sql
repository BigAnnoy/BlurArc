-- v0.7 字段迁移脚本
-- ⚠️ 此脚本仅供一次性手动执行；重复执行会因列已存在而报错。
-- 推荐使用 database.init_db() 中的幂等迁移逻辑，它会自动检测列是否存在。
-- 如需手动执行：sqlite3 ~/Documents/BlurArc/.config/photo_manager.db < backend/migrations/2026_06_25_add_v0.7_fields.sql

-- 收藏时间
ALTER TABLE photos ADD COLUMN favorited_at DATETIME;
CREATE INDEX IF NOT EXISTS ix_photos_favorited_at ON photos (favorited_at);

-- 相册封面
ALTER TABLE albums ADD COLUMN cover_photo_id INTEGER REFERENCES photos(id);

-- 相册照片加入时间
ALTER TABLE album_photos ADD COLUMN added_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- 手动排序（v0.7 字段先建但不实现拖动重排）
ALTER TABLE album_photos ADD COLUMN sort_order INTEGER DEFAULT 0;

-- XMP 标题和描述
ALTER TABLE photos ADD COLUMN title VARCHAR(255);
ALTER TABLE photos ADD COLUMN description TEXT;
