"""
sync_to_db.py — D12 综合实战（上）
将 D4 tool_executions + preferences 同步到 D11 的 SQLite
写入 sync.log 日志
"""
import json
import sqlite3
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "d11", "memory.db")
LOG_PATH = os.path.join(SCRIPT_DIR, "sync.log")
PHASE2_DIR = os.path.join(SCRIPT_DIR, "..", "phase2-consolidate")

log_lines = []

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_lines.append(line)

def sync_tool_executions():
    """同步 tool_executions.json → SQLite"""
    src = os.path.join(PHASE2_DIR, "tool_executions.json")
    if not os.path.exists(src):
        log(f"[WARN] tool_executions.json not found: {src}")
        return

    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 确保 tool_executions 表存在
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tool_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT UNIQUE,
            tool TEXT,
            status TEXT,
            output_clean TEXT,
            exec_ms INTEGER
        )
    """)

    inserted = 0
    for t in data:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO tool_executions (trace_id, tool, status, output_clean, exec_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (t.get("trace_id"), t.get("tool"), t.get("status"),
                  t.get("output_clean"), t.get("exec_ms", 0)))
            inserted += 1
        except Exception as e:
            log(f"[ERROR] Failed to insert {t.get('trace_id')}: {e}")

    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM tool_executions").fetchone()[0]
    log(f"  tool_executions: synced {inserted} records, total {count}")
    conn.close()


def sync_preferences():
    """同步 preferences.json → SQLite"""
    src = os.path.join(PHASE2_DIR, "preferences.json")
    if not os.path.exists(src):
        log(f"[WARN] preferences.json not found: {src}")
        return

    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    inserted = 0
    for p in data:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO preferences (uid, pref_key, pref_value, version, source_session)
                VALUES (?, ?, ?, ?, ?)
            """, (p.get("uid"), p.get("pref_key"), p.get("pref_value"),
                  p.get("version"), p.get("source_session")))
            inserted += 1
        except Exception as e:
            log(f"[ERROR] Failed to insert pref {p.get('pref_key')}: {e}")

    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM preferences").fetchone()[0]
    log(f"  preferences: synced {inserted} records, total {count}")
    conn.close()


def main():
    log("=" * 50)
    log("D12 sync_to_db.py — Synchronizing Phase 2 data to SQLite")
    log(f"Database: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        log(f"[ERROR] Database not found! Run D11 import_data.py first.")
        log("Sync aborted.")
        return

    sync_tool_executions()
    sync_preferences()

    # Verify counts
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables = ["preferences", "knowledge_items", "tool_executions"]
    for tbl in tables:
        try:
            cnt = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            log(f"  DB CHECK: {tbl} = {cnt} rows")
        except:
            log(f"  DB CHECK: {tbl} table not found")
    conn.close()

    log("Sync complete!")

    # Write log file
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print(f"\nLog written to {LOG_PATH}")


if __name__ == "__main__":
    main()
