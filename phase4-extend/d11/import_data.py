"""
import_data.py — D11 数据导入脚本
从 camp-data/standard/d4/ 导入 preferences 和 knowledge_items 到 SQLite memory.db
"""
import json
import sqlite3
import os
import sys

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "memory.db")
CAMP_DATA = os.path.join(SCRIPT_DIR, "..", "camp-info-main", "camp-data", "standard", "d4")

def import_preferences():
    """从 preferences.json 导入 4 条偏好记录"""
    pref_path = os.path.join(CAMP_DATA, "preferences.json")
    if not os.path.exists(pref_path):
        print(f"[WARN] preferences.json not found at {pref_path}, trying local...")
        pref_path = os.path.join(SCRIPT_DIR, "..", "preferences.json")

    with open(pref_path, "r", encoding="utf-8") as f:
        preferences = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for p in preferences:
        cur.execute("""
            INSERT OR REPLACE INTO preferences (uid, pref_key, pref_value, version, source_session)
            VALUES (?, ?, ?, ?, ?)
        """, (p.get("uid", ""), p.get("pref_key", ""), p.get("pref_value", ""),
              p.get("version", ""), p.get("source_session", None)))

    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM preferences").fetchone()[0]
    print(f"  preferences: imported {len(preferences)} records, total {count}")
    conn.close()


def import_knowledge_items():
    """从 knowledge_items.json 导入 2 条知识条目"""
    know_path = os.path.join(CAMP_DATA, "knowledge_items.json")
    if not os.path.exists(know_path):
        print(f"[WARN] knowledge_items.json not found at {know_path}, trying local...")
        know_path = os.path.join(SCRIPT_DIR, "..", "knowledge_items.json")

    with open(know_path, "r", encoding="utf-8") as f:
        knowledge = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for k in knowledge:
        tags = json.dumps(k.get("tags", []), ensure_ascii=False)
        steps = json.dumps(k.get("steps", []), ensure_ascii=False) if k.get("steps") else None
        cur.execute("""
            INSERT OR REPLACE INTO knowledge_items (title, tags, steps, notes)
            VALUES (?, ?, ?, ?)
        """, (k.get("title", ""), tags, steps, k.get("notes", "")))

    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM knowledge_items").fetchone()[0]
    print(f"  knowledge_items: imported {len(knowledge)} records, total {count}")
    conn.close()


def main():
    print("=" * 60)
    print("  D11 Data Import Script")
    print(f"  Database: {DB_PATH}")
    print("=" * 60)

    # Ensure schema exists
    schema_path = os.path.join(SCRIPT_DIR, "schema.sql")
    if os.path.exists(schema_path):
        conn = sqlite3.connect(DB_PATH)
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        print("  schema.sql executed")

    import_preferences()
    import_knowledge_items()
    print("\n[DONE] Import complete!")


if __name__ == "__main__":
    main()
