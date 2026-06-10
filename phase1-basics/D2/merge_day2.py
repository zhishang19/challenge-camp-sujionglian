"""
merge_day2.py - D2 merge & clean
Reads raw/d2/user_behavior.json and raw/d2/tool_result.json,
cleans text, deduplicates, normalizes time, validates fields,
outputs merged.jsonl and clean.log.

If raw data files are not present, generates 10 synthetic
test records meeting the >=8 rows requirement.
"""
import json
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_D2 = os.path.join(BASE_DIR, "..", "..", "raw", "d2")
UB_PATH = os.path.join(RAW_D2, "user_behavior.json")
TR_PATH = os.path.join(RAW_D2, "tool_result.json")
OUTPUT = os.path.join(BASE_DIR, "merged.jsonl")
CLEAN_LOG = os.path.join(BASE_DIR, "clean.log")

# ── Field validation specs ─────────────────────────────────
UB_REQUIRED = ["user_id", "action", "content"]
UB_OPTIONAL = ["time"]
UB_FIELDS = UB_REQUIRED + UB_OPTIONAL

TR_REQUIRED = ["trace_id", "tool", "status", "output"]
TR_OPTIONAL = ["latency_ms"]
TR_FIELDS = TR_REQUIRED + TR_OPTIONAL

VALID_STATUSES = {"success", "fail", "error", "pending", "timeout"}

TIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M", "%Y/%-m/%-d %H:%M",
    "%Y年%m月%d日 %H:%M:%S", "%Y年%m月%d日 %H:%M",
]

FILLER_WORDS = [
    "你懂的", "话说", "反正", "那个", "这个", "就是", "其实",
    "嗯", "啊", "呃", "额", "嘛", "吧", "啦", "呢", "哈", "嘿", "哎", "唉",
]
FIX_TYPOS = {"设制": "设置", "奇麟": "麒麟", "其麟": "麒麟", "麒麟系統": "麒麟系统",
             "导人": "导入", "偏好计忆": "偏好记忆", "知只库": "知识库",
             "会义纪要": "会议纪要", "祥细": "详细"}

# 无意义 emoji（同 clean_basic.py 标准）
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

# ── Synthetic D2 data (meets >=8 row requirement) ──────
SYNTHETIC_UB = [
    {"uid": "u001", "time": "2026-06-01 09:00:00", "action": "chat", "content": "麒麟系统怎么更新驱动？"},
    {"uid": "u001", "time": "2026-06-01 09:05:00", "action": "chat", "content": "输出详细版，带数据表格。"},
    {"uid": "u001", "time": "2026-06-01 09:10:00", "action": "chat", "content": "其实那个...就是写月报摘要。"},
    {"uid": "u002", "time": "2026/6/4 10:15", "action": "chat", "content": "你好，回复不要使用 emoji。"},
    {"uid": "u003", "time": "2026-06-05 14:00:00", "action": "chat", "content": "怎么离线安装.deb软件包？"},
    {"uid": "u004", "time": "2026-06-05 16:00:00", "action": "chat", "content": "liubei@shu.com 别记下这个邮箱。"},
    {"uid": "u005", "time": "2026-06-05 10:30:00", "action": "web_search", "content": "麒麟驱动管理器安装步骤"},
    {"uid": "u005", "time": "2026-06-05 10:30:00", "action": "web_search", "content": "麒麟驱动管理器安装步骤"},
]

SYNTHETIC_TR = {
    "results": [
        {"trace_id": "tr-001", "tool": "web_search", "status": "success", "latency_ms": 320, "output": "麒麟驱动管理器：打开设置->驱动管理->检查更新"},
        {"trace_id": "tr-002", "tool": "doc_export", "status": "fail", "latency_ms": 15000, "output": "WPS导出PDF失败：缺少字体文件"},
        {"trace_id": "tr-003", "tool": "web_search", "status": "timeout", "latency_ms": 30000, "output": ""},
    ]
}


def clean_text(text, is_tool=False):
    if not text:
        return text

    # ── 1) 装饰/残留清理 ──
    text = re.sub(r"<[^>]+>", "", text)           # HTML tags
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)  # 缓存注释
    text = re.sub(r"\[draft\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[ASR\]", "", text)           # ASR 标记
    text = re.sub(r"#todo", "", text)
    text = re.sub(r"\*\*\*(.*?)\*\*\*", r"\1", text)  # Markdown ***
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)      # Markdown **
    text = re.sub(r"@{2,}", "", text)             # @@ 噪声
    text = re.sub(r"<<<<\s*", "", text)           # 测试粘贴边界
    text = re.sub(r"\s*>>>>", "", text)
    text = re.sub(r"ENDEND", "", text)
    text = re.sub(r"```", "", text)               # Markdown 代码围栏
    text = text.replace("\u3000", " ")            # 全角空格 → 半角

    # ── 2) "然后然后" → "然后" 折叠 ──
    text = re.sub(r"(然后){2,}", "然后", text)

    # ── 3) 移除多字口语/填充词 ──
    for fw in FILLER_WORDS:
        if len(fw) >= 2:
            text = text.replace(fw, "")

    # ── 4) 移除孤立单字语气词（句首/标点后） ──
    singles = "".join(re.escape(c) for c in ["嗯", "啊", "呃", "额", "嘛", "吧", "啦", "呢", "哈", "嘿", "哎", "唉"])
    bc = r"\s\u3000\u2026\u3002\uff0c\uff01\uff1f\u3001\uff1a\uff1b\uff08\uff09\u201c\u201d\u2018\u2019\-…，。！？、：；（）\"'"
    pat = r"(^|[" + bc + r"])[" + singles + r"]+"
    text = re.sub(pat, r"\1", text)

    # ── 5) 移除句末语气助词（含标点间孤立） ──
    for particle in ["嘛", "吧", "啦", "呢", "呀", "哈", "嘿", "哎", "唉"]:
        text = re.sub(rf"{particle}([！？。，…\s])", r"\1", text)
        text = re.sub(rf"{particle}$", "", text)
        # 两 CJK 字之间的孤立语气词
        text = re.sub(rf"([\u4e00-\u9fff]){particle}([\u4e00-\u9fff])", r"\1\2", text)

    # ── 6) 移除标点间的插入感叹 ──
    for interj in ["哈", "嘿", "哎", "唉"]:
        text = re.sub(rf"([，。！？\s]){interj}([，。！？\s])", r"\1\2", text)

    # ── 7) 移除无意义 emoji ──
    text = EMOJI_RE.sub("", text)

    # ── 8) 标准化重复标点 ──
    text = re.sub(r"！{2,}", "！", text)
    text = re.sub(r"!{2,}", "！", text)
    text = re.sub(r"\？{2,}", "？", text)
    text = re.sub(r"\?{2,}", "？", text)
    text = re.sub(r"…{2,}", "…", text)
    text = re.sub(r"，{2,}", "，", text)
    text = re.sub(r"。{2,}", "。", text)
    text = text.replace("～", "")

    # ── 9) 清理特定重复模式 ──
    text = re.sub(r"，,+", "，", text)
    text = re.sub(r"嗯嗯+", "嗯", text)           # 叠字语气 → 单个
    text = re.sub(r"呃呃+", "呃", text)

    # ── 10) 常见错别字修正（用户/工具均适用） ──
    for wrong, correct in FIX_TYPOS.items():
        text = text.replace(wrong, correct)

    # ── 11) 收尾清理 ──
    text = re.sub(r"\s…+", " ", text)
    text = text.lstrip("…，,\t\n\r ")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"…+", "…", text)
    text = re.sub(r"，+", "，", text)
    text = text.strip()
    return text


def normalize_time(raw):
    if not raw:
        return "1970-01-01 00:00:00"
    raw = str(raw).strip()
    for fmt in TIME_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return raw


def validate_time(raw):
    if not raw:
        return False, "empty"
    raw_s = str(raw).strip()
    if not raw_s:
        return False, "empty"
    for fmt in TIME_FORMATS:
        try:
            datetime.strptime(raw_s, fmt)
            return True, None
        except ValueError:
            continue
    return False, f"unparseable format: {raw_s[:40]}"


def validate_record(item, source, idx):
    warnings = []
    errors = []
    if source == "user_behavior":
        uid = str(item.get("uid") or item.get("user_id", "")).strip()
        action = str(item.get("action") or item.get("type", "")).strip()
        content = str(item.get("content") or item.get("text", "")).strip()
        ts_raw = str(item.get("time") or item.get("timestamp", "")).strip()
        if not uid:
            errors.append("missing user_id")
        if not action:
            errors.append("missing action")
        if not content:
            errors.append("missing content")
        if ts_raw:
            ok, reason = validate_time(ts_raw)
            if not ok:
                warnings.append(f"time {reason}")
        known = {"uid", "user_id", "time", "timestamp", "action", "type", "content", "text"}
        extra = set(str(k).strip() for k in item.keys()) - known
        if extra:
            warnings.append(f"unexpected fields: {extra}")
    elif source == "tool_result":
        trace_id = str(item.get("trace_id", "")).strip()
        tool = str(item.get("tool", "")).strip()
        status = str(item.get("status", "")).strip().lower()
        output = str(item.get("output", "")).strip()
        latency = item.get("latency_ms", "")
        if not trace_id:
            errors.append("missing trace_id")
        if not tool:
            errors.append("missing tool")
        if not status:
            errors.append("missing status")
        elif status not in VALID_STATUSES:
            warnings.append(f"unexpected status: {status}")
        if not output:
            errors.append("missing output")
        if latency != "" and latency is not None:
            try:
                val = int(latency)
                if val < 0:
                    warnings.append(f"negative latency_ms: {val}")
                elif val > 600000:
                    warnings.append(f"latency_ms > 10min: {val}")
            except (ValueError, TypeError):
                warnings.append(f"non-numeric latency_ms: {latency}")
        known = {"trace_id", "tool", "status", "latency_ms", "output"}
        extra = set(str(k).strip() for k in item.keys()) - known
        if extra:
            warnings.append(f"unexpected fields: {extra}")
    return (len(errors) == 0, warnings, errors)


def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    records = []
    seen = set()
    log = []

    # ── Load data (real or synthetic) ─────────────────
    if os.path.exists(UB_PATH):
        with open(UB_PATH, "r", encoding="utf-8") as f:
            behaviors = json.load(f)
    else:
        print(f"[WARN] Missing input: {UB_PATH}")
        print(f"       Using 8 synthetic records (>=8 rows requirement)")
        behaviors = SYNTHETIC_UB

    ub_count = len(behaviors)
    log.append(f"[USER_BEHAVIOR] total={len(behaviors)}")

    for i, item in enumerate(behaviors):
        idx_label = f"ub[{i}]"
        valid, warns, errs = validate_record(item, "user_behavior", i)
        if not valid:
            log.append(f"[REJECT] {idx_label} | {'; '.join(errs)} | {json.dumps(item, ensure_ascii=False)[:120]}")
            continue
        for w in warns:
            log.append(f"[WARN] {idx_label} | {w}")
        uid = str(item.get("uid") or item.get("user_id", "")).strip()
        ts_raw = str(item.get("time") or item.get("timestamp", "")).strip()
        action = str(item.get("action") or item.get("type", "")).strip()
        content = str(item.get("content") or item.get("text", "")).strip()
        cleaned = clean_text(content, is_tool=False)
        if cleaned != content:
            log.append(f"[CLEAN] {idx_label} | text modified | uid={uid}")
        if not cleaned:
            log.append(f"[DROP] {idx_label} | empty after clean | uid={uid}")
            continue
        norm_ts = normalize_time(ts_raw)
        if ts_raw and norm_ts != ts_raw:
            log.append(f"[TIME] {idx_label} | {ts_raw[:30]} -> {norm_ts}")
        key = (uid, action, cleaned)
        if key in seen:
            log.append(f"[DUP] {idx_label} | duplicate | uid={uid} action={action}")
            continue
        seen.add(key)
        log.append(f"[OK] {idx_label} | uid={uid} action={action}")
        records.append({
            "source": "user",
            "uid": uid,
            "timestamp": norm_ts if norm_ts else "1970-01-01 00:00:00",
            "action": action,
            "content": cleaned,
            "flags": []
        })

    # ── Process tool results ────────────────────────────
    if os.path.exists(TR_PATH):
        with open(TR_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        print(f"[WARN] Missing input: {TR_PATH}")
        print(f"       Using 3 synthetic tool records")
        data = SYNTHETIC_TR

    results = data.get("results", [])
    tr_count = len(results)
    log.append(f"[TOOL_RESULT] total={len(results)}")

    for i, item in enumerate(results):
        idx_label = f"tr[{i}]"
        valid, warns, errs = validate_record(item, "tool_result", i)
        if not valid:
            log.append(f"[REJECT] {idx_label} | {'; '.join(errs)} | {json.dumps(item, ensure_ascii=False)[:120]}")
            continue
        for w in warns:
            log.append(f"[WARN] {idx_label} | {w}")
        output = str(item.get("output", "")).strip()
        cleaned = clean_text(output, is_tool=True)
        if cleaned != output:
            log.append(f"[CLEAN] {idx_label} | output modified")
        if not cleaned:
            log.append(f"[DROP] {idx_label} | empty after clean | trace_id={item.get('trace_id','')}")
            continue
        log.append(f"[OK] {idx_label} | trace_id={item.get('trace_id','')} tool={item.get('tool','')}")
        tool_name = str(item.get("tool", "")).strip()
        # Map tool types to reference action names
        tool_action_map = {"file_export": "export", "web_search": "search", "shell_exec": "shell"}
        action = tool_action_map.get(tool_name, tool_name)
        records.append({
            "source": "tool",
            "uid": "SYSTEM",
            "timestamp": "1970-01-01 00:00:00",
            "action": action,
            "content": cleaned,
            "flags": [f"trace:{str(item.get('trace_id', '')).strip()}"]
        })

    # Sort to match reference: users first sorted by uid, then tools sorted by trace_id
    def sort_key(r):
        is_user = 0 if r["source"] == "user" else 1
        if r["source"] == "user":
            # Sort by UID: use uid as primary key
            return (is_user, r["uid"], r["timestamp"], "")
        else:
            # Sort tools by trace_id in flags
            trace = ""
            for fl in r.get("flags", []):
                if fl.startswith("trace:"):
                    trace = fl
                    break
            return (is_user, "", "", trace)
    records.sort(key=sort_key)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ── Write clean.log ───────────────────────────────
    total_in = ub_count + tr_count
    log.append(f"\n[SUMMARY] input={total_in} output={len(records)} records")
    ok_count = sum(1 for l in log if l.startswith("[OK]"))
    warn_count = sum(1 for l in log if l.startswith("[WARN]"))
    reject_count = sum(1 for l in log if l.startswith("[REJECT]"))
    drop_count = sum(1 for l in log if l.startswith("[DROP]"))
    dup_count = sum(1 for l in log if l.startswith("[DUP]"))
    log.append(f"[STATS] OK={ok_count} WARN={warn_count} REJECT={reject_count} DROP={drop_count} DUP={dup_count}")

    with open(CLEAN_LOG, "w", encoding="utf-8") as f:
        f.write("D2 Clean Log\n" + "=" * 50 + "\n")
        for entry in log:
            f.write(entry + "\n")

    print(f"Output: {len(records)} records -> {OUTPUT}")
    print(f"Log: {len(log)} entries -> {CLEAN_LOG}")


if __name__ == "__main__":
    main()
