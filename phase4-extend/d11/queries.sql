-- D11 数据库查询 SQL
-- ========================================

-- 4.1 查询 uid='U001' 的所有偏好
SELECT * FROM preferences WHERE uid = 'U001';

-- 4.2 关键词查询 knowledge_items 标题含「deb」的记录
SELECT * FROM knowledge_items WHERE title LIKE '%deb%' OR tags LIKE '%deb%';

-- 4.3 导出 knowledge_items 为 CSV
-- （通过 Python sqlite3 或 .mode csv 导出）
.mode csv
.headers on
.output knowledge_export.csv
SELECT * FROM knowledge_items;
.output stdout

-- 验证 COUNT
SELECT COUNT(*) FROM preferences;   -- 期望 4
SELECT COUNT(*) FROM knowledge_items; -- 期望 2
