-- D11 数据库建表 SQL
-- 用于 memory.db (SQLite)

-- preferences 偏好记忆表
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    pref_key TEXT NOT NULL,
    pref_value TEXT NOT NULL,
    version TEXT NOT NULL,
    source_session TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- knowledge_items 知识记忆表
CREATE TABLE IF NOT EXISTS knowledge_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    tags TEXT NOT NULL,          -- JSON 数组字符串，如 '["麒麟","安装"]'
    steps TEXT,                  -- JSON 数组字符串
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- tool_executions 工具执行记录表（D12 扩展）
CREATE TABLE IF NOT EXISTS tool_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT UNIQUE,
    tool TEXT,
    status TEXT,
    output_clean TEXT,
    exec_ms INTEGER
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_pref_uid ON preferences(uid);
CREATE INDEX IF NOT EXISTS idx_know_title ON knowledge_items(title);
CREATE INDEX IF NOT EXISTS idx_tool_trace ON tool_executions(trace_id);
