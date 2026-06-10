"""
setup_db.py — Phase 4 SQLite Database Setup
============================================
Creates memory.db with 5 tables, imports data from phase2-consolidate JSON files,
runs sample queries, and exports results to CSV.

Tables:
  - knowledge_items   (id, title, body, tags, type, source)
  - preferences       (uid, pref_key, pref_value, type, version, ttl)
  - chat_turns        (session_id, user_id, role, message, created_at)
  - tool_executions   (tool_id, source, content, status, duration_ms, trace_id)
  - memory_snapshots  (uid, key, memory_value, version, scope, last_seen)

Usage:
  py phase4-extend/setup_db.py
"""
import json
import os
import sqlite3
import csv
import time

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DATA_DIR = os.path.join(ROOT, "phase2-consolidate")
DB_PATH = os.path.join(BASE, "memory.db")

DATA_FILES = {
    "knowledge_items": "knowledge_items.json",
    "preferences": "preferences.json",
    "chat_turns": "chat_turns.json",
    "tool_executions": "tool_executions.json",
    "memory_snapshots": "memory_snapshots_resolved.json",
}


def load_json(name):
    path = os.path.join(DATA_DIR, DATA_FILES[name])
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"[WARN] {path} not found, using empty list")
    return []


def create_tables(conn):
    """Create all 5 tables in SQLite."""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id TEXT PRIMARY KEY,
            title TEXT,
            body TEXT,
            tags TEXT,
            type TEXT,
            source TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT,
            pref_key TEXT,
            pref_value TEXT,
            type TEXT,
            version TEXT,
            ttl TEXT,
            confidence TEXT,
            source TEXT,
            time TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_id TEXT,
            role TEXT,
            message TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tool_executions (
            tool_id TEXT PRIMARY KEY,
            source TEXT,
            content TEXT,
            status TEXT,
            duration_ms TEXT,
            trace_id TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT,
            key TEXT,
            memory_value TEXT,
            version TEXT,
            scope TEXT,
            last_seen TEXT,
            source TEXT
        )
    """)

    conn.commit()


def import_data(conn):
    """Import all JSON data into SQLite tables."""
    cur = conn.cursor()

    # 1) knowledge_items
    items = load_json("knowledge_items")
    for item in items:
        cur.execute(
            "INSERT OR REPLACE INTO knowledge_items VALUES (?, ?, ?, ?, ?, ?)",
            (item.get("id"), item.get("title"), item.get("body"),
             json.dumps(item.get("tags", []), ensure_ascii=False),
             item.get("type"), item.get("source"))
        )
    print(f"  knowledge_items: {len(items)} rows imported")

    # 2) preferences
    prefs = load_json("preferences")
    for p in prefs:
        cur.execute(
            "INSERT INTO preferences (uid, pref_key, pref_value, type, version, ttl, confidence, source, time) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (p.get("uid"), p.get("pref_key"), p.get("pref_value"),
             p.get("type"), p.get("version"), p.get("ttl"),
             p.get("confidence"), p.get("source"), p.get("time"))
        )
    print(f"  preferences: {len(prefs)} rows imported")

    # 3) chat_turns
    turns = load_json("chat_turns")
    for t in turns:
        cur.execute(
            "INSERT INTO chat_turns (session_id, user_id, role, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (t.get("session_id"), t.get("user_id"), t.get("role"),
             t.get("message"), t.get("created_at"))
        )
    print(f"  chat_turns: {len(turns)} rows imported")

    # 4) tool_executions
    tools = load_json("tool_executions")
    for t in tools:
        cur.execute(
            "INSERT OR REPLACE INTO tool_executions VALUES (?, ?, ?, ?, ?, ?)",
            (t.get("tool_id"), t.get("source"), t.get("content"),
             t.get("status"), str(t.get("duration_ms", "")),
             t.get("trace_id"))
        )
    print(f"  tool_executions: {len(tools)} rows imported")

    # 5) memory_snapshots
    snaps = load_json("memory_snapshots")
    for s in snaps:
        cur.execute(
            "INSERT INTO memory_snapshots (uid, key, memory_value, version, scope, last_seen, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (s.get("uid"), s.get("key"), s.get("memory_value"),
             s.get("version"), s.get("scope"), s.get("last_seen"),
             s.get("source"))
        )
    print(f"  memory_snapshots: {len(snaps)} rows imported")

    conn.commit()


def run_queries(conn):
    """Run sample queries and print results."""
    cur = conn.cursor()

    print("\n" + "=" * 50)
    print("  Sample Queries")
    print("=" * 50)

    # Q1: Count per table
    for table in ["knowledge_items", "preferences", "chat_turns",
                   "tool_executions", "memory_snapshots"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} records")

    # Q2: Preferences by user
    print("\n  --- Preferences by User ---")
    cur.execute("SELECT uid, COUNT(*) FROM preferences GROUP BY uid")
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]} preference(s)")

    # Q3: Knowledge items with麒麟 tag
    print("\n  --- Knowledge tagged '麒麟' ---")
    cur.execute("SELECT id, title FROM knowledge_items WHERE tags LIKE '%麒麟%'")
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]}")

    # Q4: Chat sessions count
    print("\n  --- Chat Sessions ---")
    cur.execute("SELECT session_id, COUNT(*) as turns FROM chat_turns GROUP BY session_id")
    for row in cur.fetchall():
        print(f"    {row[0]}: {row[1]} turns")

    # Q5: Memory snapshots with scope='deleted' (forgotten items)
    print("\n  --- Forgotten Memory Items ---")
    cur.execute("SELECT uid, key, memory_value FROM memory_snapshots WHERE scope='deleted'")
    rows = cur.fetchall()
    if rows:
        for row in rows:
            print(f"    {row[0]}: {row[1]} -> {row[2]}")
    else:
        print("    (none)")


def export_csv(conn):
    """Export all tables to CSV files."""
    export_dir = os.path.join(BASE, "exports")
    os.makedirs(export_dir, exist_ok=True)

    tables = ["knowledge_items", "preferences", "chat_turns",
              "tool_executions", "memory_snapshots"]

    for table in tables:
        path = os.path.join(export_dir, f"{table}.csv")
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            writer.writerows(rows)

        print(f"  {table}.csv: {len(rows)} rows -> {path}")

    print(f"\n  CSV files exported to: {export_dir}")


def main():
    print("=" * 50)
    print("  Phase 4 — SQLite Database Setup")
    print("=" * 50)

    start = time.time()

    conn = sqlite3.connect(DB_PATH)
    print(f"\n[1/4] Creating tables ...")
    create_tables(conn)

    print(f"\n[2/4] Importing data ...")
    import_data(conn)

    print(f"\n[3/4] Running queries ...")
    run_queries(conn)

    print(f"\n[4/4] Exporting CSV ...")
    export_csv(conn)

    conn.close()

    elapsed = time.time() - start
    db_size = os.path.getsize(DB_PATH) / 1024

    print(f"\n{'=' * 50}")
    print(f"  Done!  memory.db created ({db_size:.1f} KB)")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Path: {DB_PATH}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
