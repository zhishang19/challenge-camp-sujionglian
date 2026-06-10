"""
consolidate_generated.py — 处理 generated/ 目录的大规模训练数据
按照 generate_memory_training_data.py --records-per-day 10000 生成的数据格式
清洗到 phase2-consolidate/，共 50,000 条记录。

Modules:
  D02: tool_result_d02.json / user_behavior_clean.json
  D03: chat_sessions_clean.csv → chat_sessions_clean.json
  D04: chat_turns.json / knowledge_items.json / preferences.json / tool_executions.json
  D05: memory_events.json / memory_snapshots_resolved.json / conflict_resolution_v5.json
  D06: quality_evaluation.json / quality_eval_report.md
  RPT: report.md
"""
import csv
import json
import os
import re
import sys
import io
from typing import Any, Dict, List, Tuple

# ═══════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
GEN = os.path.join(ROOT, "generated")
OUT = BASE

# ═══════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════

# 停顿/口语词
FILLER_WORDS = [
    "嗯", "啊", "呃", "额", "那个", "这个", "就是", "其实",
    "嘛", "吧", "啦", "呢", "话说", "反正", "哈", "嘿", "哎", "唉", "你懂的",
]
# 常见错别字
FIX_TYPOS = {
    "奇麟": "麒麟", "其麟": "麒麟", "麒麟系統": "麒麟系统",
    "设制": "设置", "导人": "导入",
    "偏好计忆": "偏好记忆", "知只库": "知识库",
    "会义纪要": "会议纪要", "祥细": "详细",
}
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"1[3-9]\d{9}")

# Emoji range for removal (无意义 emoji)
EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\u2600-\u27BF"
    "\uFE00-\uFE0F"
    "\u200D"
    "\u20E3"
    "]"
)


def norm_time(ts: str) -> str:
    """Normalize timestamp to YYYY-MM-DD HH:MM:SS."""
    if not ts or not ts.strip():
        return ""
    ts = ts.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", ts):
        return ts
    m = re.match(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})", ts)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})[\s_]+(\d{1,2}:\d{2}(?::\d{2})?)", ts)
    if m:
        tp = m.group(4)
        parts = tp.split(":")
        h = int(parts[0]); mi = parts[1]; s = parts[2] if len(parts) > 2 else "00"
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} {h:02d}:{mi}:{s}"
    m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}:\d{2}(?::\d{2})?)", ts)
    if m:
        tp = m.group(4)
        parts = tp.split(":")
        h = int(parts[0]); mi = parts[1]; s = parts[2] if len(parts) > 2 else "00"
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} {h:02d}:{mi}:{s}"
    return ts


def clean_text(text: str) -> Tuple[str, Dict]:
    """Clean text: fillers, symbols, typos, PII, emoji. Returns (clean, meta)."""
    meta: Dict[str, List] = {}
    t = text.strip()

    # ── PII redaction ──
    sensitive = []
    for m in EMAIL_RE.finditer(t):
        sensitive.append(m.group())
    for m in PHONE_RE.finditer(t):
        sensitive.append(m.group())
    if sensitive:
        meta["sensitive_redacted"] = list(set(sensitive))
        for s in sensitive:
            t = t.replace(s, "[REDACTED]")

    # ── Noise markers (before filler removal) ──
    t = re.sub(r"\[ASR\]", "", t)
    t = re.sub(r"\[draft\]", "", t, flags=re.IGNORECASE)
    t = re.sub(r"#todo", "", t)
    t = re.sub(r"<!--.*?-->", "", t)
    t = re.sub(r"<<<<\s*", "", t)
    t = re.sub(r"\s*>>>>", "", t)
    t = re.sub(r"<p>|</p>|<br/?>", "", t)
    t = re.sub(r"ENDEND", "", t)
    t = re.sub(r"（口述）", "", t)
    t = re.sub(r"\bcache=false\b", "", t)
    t = re.sub(r"```", "", t)
    t = re.sub(r"help:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\(口述\)", "", t)
    t = re.sub(r"\[draft\]", "", t, flags=re.IGNORECASE)
    t = t.replace("\u3000", " ")

    # ── Dedup specific patterns ──
    had_dedup_then = "然后然后" in t
    t = re.sub(r"(然后){2,}", "然后", t)
    t = re.sub(r"嗯嗯+", "嗯", t)
    t = re.sub(r"呃呃+", "呃", t)
    t = re.sub(r"啊啊+", "啊", t)

    # ── Remove leading filler patterns ──
    filler_removed = []

    m = re.match(r"^[嗯啊呃额]…[那个就是这]{1,2}…", t)
    if m:
        removed_part = m.group()
        for fw in FILLER_WORDS:
            if fw in removed_part:
                filler_removed.append(fw)
        t = t[m.end():].strip()

    if not filler_removed:
        m = re.match(r"^[嗯啊呃额]…", t)
        if m:
            removed_part = m.group()
            for fw in FILLER_WORDS:
                if fw in removed_part:
                    filler_removed.append(fw)
            t = t[m.end():].strip()

    if not filler_removed:
        for leading in [
            "就是 ", "那个 ", "这个 ", "嗯 ", "呃 ", "啊 ", "额 ",
            "其实 ", "话说 ", "反正 ", "你懂的 ", "我想想 ", "麻烦 ",
            "稍等 ", "help: ", "help：",
        ]:
            if t.startswith(leading):
                fw = leading.strip().rstrip(":：")
                for f in FILLER_WORDS:
                    if f in fw and f not in filler_removed:
                        filler_removed.append(f)
                t = t[len(leading):].strip()
                break

    if "你懂的" in t:
        if "你懂的" not in filler_removed:
            filler_removed.append("你懂的")
        t = t.replace("你懂的", "")

    if had_dedup_then and "然后" not in filler_removed:
        filler_removed.append("然后")

    if filler_removed:
        meta["filler_removed"] = filler_removed

    # ── Symbols / decorations ──
    symbols_found = []
    if "【" in t or "】" in t:
        symbols_found.extend(["【", "】"])
    if re.search(r"@{2,}", t):
        symbols_found.append("@@@")
    if re.search(r"\*\*", t):
        symbols_found.append("**")
    if "～" in t:
        symbols_found.append("～")
    if symbols_found:
        meta["symbols_removed"] = list(dict.fromkeys(symbols_found))

    t = re.sub(r"【(.*?)】", r"\1", t)
    t = re.sub(r"【|】", "", t)
    t = re.sub(r"@{2,}", "", t)
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)
    t = re.sub(r"\*\*", "", t)
    t = t.replace("～", "")

    # ── Remove emoji ──
    t = EMOJI_RE.sub("", t)

    # ── Normalize repeated punctuation ──
    t = re.sub(r"！{2,}", "！", t)
    t = re.sub(r"!{2,}", "！", t)
    t = re.sub(r"\？{2,}", "？", t)
    t = re.sub(r"\?{2,}", "？", t)
    t = re.sub(r"…{2,}", "…", t)
    t = re.sub(r"，{2,}", "，", t)
    t = re.sub(r"。{2,}", "。", t)

    # ── Remove sentence-final modal particles ──
    for particle in ["嘛", "吧", "啦", "呢", "呀", "哈", "嘿", "哎", "唉"]:
        t = re.sub(rf"{particle}([！？。，…\s])", r"\1", t)
        t = re.sub(rf"{particle}$", "", t)
        t = re.sub(rf"([\u4e00-\u9fff]){particle}([\u4e00-\u9fff])", r"\1\2", t)

    # ── Standalone interjections between punctuation ──
    for interj in ["哈", "嘿", "哎", "唉"]:
        t = re.sub(rf"([，。！？\s]){interj}([，。！？\s])", r"\1\2", t)

    # ── Collapse whitespace ──
    t = re.sub(r"\s{2,}", " ", t)
    t = t.strip()

    # ── Typos ──
    typos_fixed = {}
    for wrong, right in FIX_TYPOS.items():
        if wrong in t:
            typos_fixed[wrong] = right
            t = t.replace(wrong, right)
    if typos_fixed:
        meta["typos_fixed"] = typos_fixed

    t = t.strip()
    return t, meta


def fix_uid(uid: str) -> str:
    if not uid or not uid.strip():
        return "UNKNOWN"
    return uid.strip().upper()


def clean_tool_output(output: str) -> str:
    """Clean tool output: reuse full text cleaning, normalize newlines."""
    output, _ = clean_text(output)
    output = re.sub(r"\n{2,}", "\n", output)
    output = output.strip()
    return output


def to_int(v) -> int:
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


# ═══════════════════════════════════════════════════
# D02 — tool_result.jsonl + user_behavior.jsonl
# ═══════════════════════════════════════════════════

def build_d02_tool_results() -> List[Dict]:
    path = os.path.join(GEN, "d02", "tool_result.jsonl")
    results = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            output = rec.get("output", "")
            results.append({
                "trace_id": rec.get("trace_id", ""),
                "tool": rec.get("tool", ""),
                "status": rec.get("status", ""),
                "output_clean": clean_tool_output(output),
                "latency_ms": to_int(rec.get("latency_ms", 0)),
            })
    return results


def build_d02_user_behavior() -> List[Dict]:
    path = os.path.join(GEN, "d02", "user_behavior.jsonl")
    results = []
    seen = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            uid = rec.get("uid") or rec.get("user_id", "")
            ts = rec.get("time") or rec.get("timestamp", "")
            action = rec.get("action") or rec.get("type", "")
            content = rec.get("content") or rec.get("text", "")

            uid = fix_uid(uid)
            ts = norm_time(ts)
            content_clean, meta = clean_text(content)

            key = (uid, ts, action, content_clean)
            if key in seen:
                continue
            seen.add(key)

            entry = {
                "uid": uid,
                "timestamp": ts,
                "action": action,
                "content_clean": content_clean,
            }
            if meta:
                entry["meta"] = meta
            results.append(entry)

    results.sort(key=lambda x: (x["timestamp"], x["uid"]))
    return results


# ═══════════════════════════════════════════════════
# D03 — chat_sessions_dirty.csv
# ═══════════════════════════════════════════════════

def build_d03_chat_sessions() -> List[Dict]:
    path = os.path.join(GEN, "d03", "chat_sessions_dirty.csv")
    results = []
    seen = set()
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            session_id = row.get("session_id", "").strip()
            user_id = fix_uid(row.get("user_id", ""))
            role = row.get("role", "").strip()
            message = row.get("message", "").strip()
            created_at = row.get("created_at", "").strip()

            if not session_id and not message:
                continue
            if not message:
                continue

            message_clean, meta = clean_text(message)
            ts = norm_time(created_at)

            key = (session_id, user_id, role, message_clean)
            if key in seen:
                continue
            seen.add(key)

            entry = {
                "session_id": session_id,
                "uid": user_id,
                "role": role,
                "message_clean": message_clean,
                "timestamp": ts,
            }
            if meta:
                entry["meta"] = meta
            results.append(entry)

    results.sort(key=lambda x: (x["timestamp"], x["session_id"]))
    return results


# ═══════════════════════════════════════════════════
# D04
# ═══════════════════════════════════════════════════

def build_d04_chat_turns() -> List[Dict]:
    path = os.path.join(GEN, "d04", "chat_logs_raw.jsonl")
    results = []
    seen = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            session = rec.get("session", "")
            uid = fix_uid(rec.get("uid", ""))
            text = rec.get("text", "")
            text_clean, meta = clean_text(text)
            ts = norm_time(rec.get("ts", ""))

            key = (session, uid, text_clean)
            if key in seen:
                continue
            seen.add(key)

            entry = {
                "session_id": session,
                "uid": uid,
                "role": rec.get("role", "user"),
                "text_clean": text_clean,
                "timestamp": ts,
            }
            if meta:
                entry["meta"] = meta
            results.append(entry)

    results.sort(key=lambda x: (x["timestamp"], x["session_id"]))
    return results


def build_d04_knowledge_items() -> List[Dict]:
    path = os.path.join(GEN, "d04", "knowledge_raw.jsonl")
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            title = rec.get("title", "")
            tags_str = rec.get("tags", "")
            body = rec.get("body", "")
            source_time = rec.get("source_time", "")

            tags = [t.strip().lstrip("#") for t in re.split(r"[#\s]+", tags_str) if t.strip().lstrip("#")]
            body_clean, meta = clean_text(body)
            body_clean = re.sub(r"```", "", body_clean)
            body_clean = body_clean.strip()

            requirements = ""
            steps = []

            for kw in ["记忆原则", "麒麟适配", "处理流程", "步骤"]:
                idx = body_clean.find(kw)
                if idx > 0:
                    rest = body_clean[idx + len(kw):]
                    rest = rest.lstrip("：:。. ")
                    if rest:
                        if "；" in rest or ";" in rest or re.search(r"\d[\.\、]", rest):
                            raw_steps = re.split(r"[；;]", rest)
                            for s in raw_steps:
                                s = s.strip().lstrip("0123456789. -")
                                if s and len(s) > 1:
                                    steps.append(s)
                        else:
                            requirements = rest
                    break

            if not requirements and not steps:
                remaining = body_clean
                for noise_title in ["离线安装 deb", "系统缓存清理", "知识库检索", "隐私设置",
                                   "驱动更新入口", "会议纪要", "密码重置"]:
                    if remaining.startswith(noise_title):
                        remaining = remaining[len(noise_title):].strip()
                        remaining = remaining.lstrip("：:。. ")
                        break
                if remaining and len(remaining) > 3:
                    requirements = remaining

            item = {
                "item_id": rec.get("item_id", ""),
                "title": title,
                "tags": tags,
                "source_time": norm_time(source_time),
            }
            if steps:
                item["steps"] = steps
            if requirements:
                item["requirements"] = requirements
            if body_clean:
                item["body_clean"] = body_clean
            items.append(item)

    return items


def build_d04_preferences() -> List[Dict]:
    path = os.path.join(GEN, "d04", "preferences_raw.csv")
    raw_prefs = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = fix_uid(row.get("uid", ""))
            key = row.get("pref_key", "").strip()
            value = row.get("pref_value", "").strip()
            version = row.get("version", "v1").strip()
            note = row.get("note", "").strip()

            value_clean, _ = clean_text(value)

            raw_prefs.append({
                "uid": uid,
                "key": key,
                "value": value_clean,
                "version": version,
                "note": note,
            })

    merged = {}
    for p in raw_prefs:
        combo = (p["uid"], p["key"])
        if combo not in merged:
            merged[combo] = p
            continue
        existing = merged[combo]
        ev = int(existing["version"].lstrip("v")) if existing["version"].startswith("v") else 0
        pv = int(p["version"].lstrip("v")) if p["version"].startswith("v") else 0
        if pv > ev:
            merged[combo] = p

    result = []
    for (uid, key), p in sorted(merged.items()):
        result.append({
            "uid": uid,
            "key": key,
            "value": p["value"],
            "version": p["version"],
        })

    return result


def build_d04_tool_executions() -> List[Dict]:
    path = os.path.join(GEN, "d04", "tool_result_raw.jsonl")
    results = []
    seen = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            trace = rec.get("trace", "")
            if trace in seen:
                continue
            seen.add(trace)

            raw_output = rec.get("raw_output", "")
            exec_ms = to_int(rec.get("exec_ms", 0))

            results.append({
                "trace_id": trace,
                "tool": rec.get("tool", ""),
                "status": rec.get("status", "unknown"),
                "output_clean": clean_tool_output(raw_output),
                "exec_ms": exec_ms,
            })

    results.sort(key=lambda x: x["trace_id"])
    return results


# ═══════════════════════════════════════════════════
# D05
# ═══════════════════════════════════════════════════

def build_d05_memory_events() -> List[Dict]:
    path = os.path.join(GEN, "d05", "memory_events_raw.jsonl")
    events = []
    seen = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            evt = json.loads(line)
            eid = evt.get("event_id", "")
            euid = fix_uid(evt.get("uid", ""))
            content = evt.get("content", "")
            content_clean, meta = clean_text(content)
            ts = norm_time(evt.get("time", ""))

            key = (eid, euid, content_clean)
            if key in seen:
                continue
            seen.add(key)

            entry = {
                "event_id": eid,
                "uid": euid,
                "source": evt.get("source", ""),
                "event_type": evt.get("event_type", ""),
                "content_clean": content_clean,
                "time": ts,
                "ttl": evt.get("ttl", ""),
                "confidence": evt.get("confidence", ""),
            }
            if meta:
                entry["meta"] = meta
            events.append(entry)

    events.sort(key=lambda x: x["event_id"])
    return events


def build_d05_snapshots() -> List[Dict]:
    path = os.path.join(GEN, "d05", "user_memory_snapshots_raw.csv")
    snapshots = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uid = fix_uid(row.get("uid", ""))
            key = row.get("memory_key", "").strip()
            value = row.get("memory_value", "").strip()
            scope = row.get("scope", "").strip()
            version = row.get("version", "v1").strip()
            last_seen = row.get("last_seen", "").strip()
            note = row.get("note", "").strip()

            if "错误写入" in note:
                continue

            value_clean, meta = clean_text(value)

            snapshots.append({
                "key": key,
                "memory_value": value_clean,
                "uid": uid,
                "version": version,
                "scope": scope,
                "last_seen": norm_time(last_seen) if last_seen else None,
                "source": "extracted" if last_seen else "synthetic",
            })

    resolved = {}
    for s in snapshots:
        combo = (s["uid"], s["key"])
        if combo not in resolved:
            resolved[combo] = s
            continue
        existing = resolved[combo]
        ev = int(existing["version"].lstrip("v")) if existing["version"].startswith("v") else 0
        sv = int(s["version"].lstrip("v")) if s["version"].startswith("v") else 0
        if sv > ev:
            resolved[combo] = s

    return sorted(resolved.values(), key=lambda x: (x["uid"], x["key"]))


def build_d05_conflicts() -> List[Dict]:
    path = os.path.join(GEN, "d05", "conflict_candidates_raw.csv")
    conflicts = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("conflict_id", "").strip()
            uid = fix_uid(row.get("uid", ""))
            old_memory = row.get("old_memory", "").strip()
            new_signal = row.get("new_signal", "").strip()
            effect = row.get("expected_effect", "").strip()
            evidence_time = row.get("evidence_time", "").strip()

            old_clean, _ = clean_text(old_memory)
            new_clean, _ = clean_text(new_signal)
            ts = norm_time(evidence_time) if evidence_time else ""

            conflicts.append({
                "conflict_id": cid,
                "uid": uid,
                "old_memory_clean": old_clean,
                "new_signal_clean": new_clean,
                "expected_effect": effect,
                "evidence_time": ts,
            })

    return conflicts


# ═══════════════════════════════════════════════════
# D06
# ═══════════════════════════════════════════════════

def build_d06_quality_eval() -> Dict:
    eval_path = os.path.join(GEN, "d06", "eval_prompts_dirty.csv")
    trace_path = os.path.join(GEN, "d06", "tool_eval_trace_raw.jsonl")

    cases = []
    with open(eval_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row.get("query", "").strip()
            query_clean, _ = clean_text(query)
            cases.append({
                "case_id": row.get("case_id", "").strip(),
                "uid": fix_uid(row.get("uid", "")),
                "query_clean": query_clean,
                "expected": row.get("expected_memory_hint", "").strip(),
                "difficulty": row.get("difficulty", "").strip(),
            })

    traces = []
    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                traces.append(json.loads(line))

    trace_map = {t["case_id"]: t for t in traces}
    results = []
    for c in cases:
        cid = c["case_id"]
        t = trace_map.get(cid, {})
        jn = t.get("judge_note", "")
        hit = jn.startswith("命中")
        leak = "严重隐私" in jn or "泄露" in jn.replace("未泄露", "")

        results.append({
            "case_id": cid,
            "uid": c["uid"],
            "query": c["query_clean"],
            "expected": c["expected"],
            "retrieved": t.get("retrieved", []),
            "answer": t.get("answer", ""),
            "judge_note": jn,
            "status": "hit" if hit and not leak else ("privacy_leak" if leak else "miss"),
        })

    hit_count = sum(1 for r in results if r["status"] == "hit")
    leak_count = sum(1 for r in results if r["status"] == "privacy_leak")
    miss_count = sum(1 for r in results if r["status"] == "miss")

    return {
        "total_cases": len(results),
        "hit": hit_count,
        "privacy_leak": leak_count,
        "miss": miss_count,
        "hit_rate": f"{hit_count/len(results)*100:.0f}%" if results else "0%",
        "results": results,
    }


# ═══════════════════════════════════════════════════
# Report
# ═══════════════════════════════════════════════════

def build_report(stats: dict) -> str:
    return f"""# Phase 2 Generated Data Consolidation Report

## Input: generated/ (--records-per-day 10000)

| Day | File | Raw | Cleaned | Dropped |
|-----|------|:---:|:---:|:---:|
| D02 | tool_result.jsonl | {stats['d02_tool_raw']} | {stats['d02_tool_out']} | {stats['d02_tool_raw'] - stats['d02_tool_out']} |
| D02 | user_behavior.jsonl | {stats['d02_ub_raw']} | {stats['d02_ub_out']} | {stats['d02_ub_raw'] - stats['d02_ub_out']} |
| D03 | chat_sessions_dirty.csv | {stats['d03_raw']} | {stats['d03_out']} | {stats['d03_raw'] - stats['d03_out']} |
| D04 | chat_logs_raw.jsonl | {stats['d04_chat_raw']} | {stats['d04_chat_out']} | {stats['d04_chat_raw'] - stats['d04_chat_out']} |
| D04 | knowledge_raw.jsonl | {stats['d04_know_raw']} | {stats['d04_know_out']} | 0 |
| D04 | preferences_raw.csv | {stats['d04_pref_raw']} | {stats['d04_pref_out']} | {stats['d04_pref_raw'] - stats['d04_pref_out']} |
| D04 | tool_result_raw.jsonl | {stats['d04_tool_raw']} | {stats['d04_tool_out']} | {stats['d04_tool_raw'] - stats['d04_tool_out']} |
| D05 | memory_events_raw.jsonl | {stats['d05_evt_raw']} | {stats['d05_evt_out']} | {stats['d05_evt_raw'] - stats['d05_evt_out']} |
| D05 | user_memory_snapshots_raw.csv | {stats['d05_snap_raw']} | {stats['d05_snap_out']} | {stats['d05_snap_raw'] - stats['d05_snap_out']} |
| D05 | conflict_candidates_raw.csv | {stats['d05_conf_raw']} | {stats['d05_conf_out']} | 0 |
| D06 | eval_prompts_dirty.csv + trace | {stats['d06_raw']} | {stats['d06_out']} | 0 |

## Cleaning Rules Applied

| Rule | Description |
|------|-------------|
| Filler words | 嗯, 啊, 呃, 那个, 就是 — removed from leading position |
| Symbol removal | 【】, @@@, ** — content preserved, wrapper stripped |
| Noise markers | [ASR], [draft], #todo, <!--cached-->, ENDEND, <<<>>>> |
| HTML tags | <p>, </p> — removed |
| Typos | 奇麟→麒麟, 其麟→麒麟, 设制→设置, 知只→知识, 会义→会议 |
| PII redaction | email → [REDACTED], phone → [REDACTED] |
| Dedup | Duplicate records removed |
| Time normalization | Multiple formats → YYYY-MM-DD HH:MM:SS |
| UID normalization | Uppercase, missing → UNKNOWN |
| Filler dedup | 然后然后 → 然后 |

## Output Files

| File | Records |
|------|:---:|
| tool_result_d02.json | {stats['d02_tool_out']} |
| user_behavior_clean.json | {stats['d02_ub_out']} |
| chat_sessions_clean.json | {stats['d03_out']} |
| chat_turns.json | {stats['d04_chat_out']} |
| knowledge_items.json | {stats['d04_know_out']} |
| preferences.json | {stats['d04_pref_out']} |
| tool_executions.json | {stats['d04_tool_out']} |
| memory_events.json | {stats['d05_evt_out']} |
| memory_snapshots_resolved.json | {stats['d05_snap_out']} |
| conflict_resolution_v5.json | {stats['d05_conf_out']} |
| quality_evaluation.json | {stats['d06_out']} |
"""


def save_json(data, filename):
    path = os.path.join(OUT, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    count = len(data) if isinstance(data, list) else "N/A"
    print(f"  {filename}: {count} records")
    return count


def count_lines(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return sum(1 for line in f if line.strip())


def count_csv_rows(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f) - 1


def main():
    print("=" * 60)
    print("  Consolidate Generated Data (50K records)")
    print("=" * 60)

    print("\n[D02] Processing tool_result.jsonl + user_behavior.jsonl")
    d02_tool = build_d02_tool_results()
    n1 = save_json(d02_tool, "tool_result_d02.json")
    d02_ub = build_d02_user_behavior()
    n2 = save_json(d02_ub, "user_behavior_clean.json")

    print("\n[D03] Processing chat_sessions_dirty.csv")
    d03 = build_d03_chat_sessions()
    n3 = save_json(d03, "chat_sessions_clean.json")

    print("\n[D04] Processing chat_logs / knowledge / preferences / tool_result")
    d04_chat = build_d04_chat_turns()
    n4 = save_json(d04_chat, "chat_turns.json")
    d04_know = build_d04_knowledge_items()
    n5 = save_json(d04_know, "knowledge_items.json")
    d04_pref = build_d04_preferences()
    n6 = save_json(d04_pref, "preferences.json")
    d04_tool = build_d04_tool_executions()
    n7 = save_json(d04_tool, "tool_executions.json")

    print("\n[D05] Processing memory_events / snapshots / conflicts")
    d05_evt = build_d05_memory_events()
    n8 = save_json(d05_evt, "memory_events.json")
    d05_snap = build_d05_snapshots()
    n9 = save_json(d05_snap, "memory_snapshots_resolved.json")
    d05_conf = build_d05_conflicts()
    n10 = save_json(d05_conf, "conflict_resolution_v5.json")

    print("\n[D06] Processing eval_prompts_dirty.csv + tool_eval_trace_raw.jsonl")
    qe = build_d06_quality_eval()
    n11 = save_json(qe, "quality_evaluation.json")
    print(f"    hit={qe['hit']}, leak={qe['privacy_leak']}, miss={qe['miss']}")

    stats = {
        "d02_tool_raw": count_lines(os.path.join(GEN, "d02", "tool_result.jsonl")),
        "d02_tool_out": n1,
        "d02_ub_raw": count_lines(os.path.join(GEN, "d02", "user_behavior.jsonl")),
        "d02_ub_out": n2,
        "d03_raw": count_csv_rows(os.path.join(GEN, "d03", "chat_sessions_dirty.csv")),
        "d03_out": n3,
        "d04_chat_raw": count_lines(os.path.join(GEN, "d04", "chat_logs_raw.jsonl")),
        "d04_chat_out": n4,
        "d04_know_raw": count_lines(os.path.join(GEN, "d04", "knowledge_raw.jsonl")),
        "d04_know_out": n5,
        "d04_pref_raw": count_csv_rows(os.path.join(GEN, "d04", "preferences_raw.csv")),
        "d04_pref_out": n6,
        "d04_tool_raw": count_lines(os.path.join(GEN, "d04", "tool_result_raw.jsonl")),
        "d04_tool_out": n7,
        "d05_evt_raw": count_lines(os.path.join(GEN, "d05", "memory_events_raw.jsonl")),
        "d05_evt_out": n8,
        "d05_snap_raw": count_csv_rows(os.path.join(GEN, "d05", "user_memory_snapshots_raw.csv")),
        "d05_snap_out": n9,
        "d05_conf_raw": count_csv_rows(os.path.join(GEN, "d05", "conflict_candidates_raw.csv")),
        "d05_conf_out": n10,
        "d06_raw": count_csv_rows(os.path.join(GEN, "d06", "eval_prompts_dirty.csv")),
        "d06_out": qe["total_cases"],
    }

    print("\n[M10] Generating report.md")
    report = build_report(stats)
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print("  report.md: generated")

    total_out = sum(v for k, v in stats.items() if k.endswith("_out"))
    print(f"\n{'=' * 60}")
    print(f"  Total output records: {total_out}")
    print(f"  All outputs in: {OUT}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
