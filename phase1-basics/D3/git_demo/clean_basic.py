"""
clean_basic.py - D3 basic clean (按批改原则重写)
Reads raw/d3/chat_sessions_dirty.csv, outputs chat_sessions_clean.csv.
Handles: empty msgs, duplicates, missing user_id, time norm, PII mask, text clean.
"""
import csv, os, re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(BASE_DIR, "..", "..", "raw", "d3", "chat_sessions_dirty.csv")
OUTPUT = os.path.join(BASE_DIR, "chat_sessions_clean.csv")
REVIEW_LOG = os.path.join(BASE_DIR, "review_log.txt")

# 停顿/口语词
FILLER_WORDS = [
    "你懂的","话说","反正","那个","这个","就是","其实",
    "嗯","啊","呃","额","嘛","吧","啦","呢","哈","嘿","哎","唉",
]
# 常见错别字
FIX_TYPOS = {
    "奇麟": "麒麟", "其麟": "麒麟", "麒麟系統": "麒麟系统",
    "设制": "设置", "导人": "导入",
    "偏好计忆": "偏好记忆", "知只库": "知识库",
    "会义纪要": "会议纪要", "祥细": "详细",
}
# 无意义 emoji
EMOJI_RE = re.compile(
    "["                           # character class
    "\U0001F600-\U0001F64F"      # emoticons
    "\U0001F300-\U0001F5FF"      # symbols & pictographs  
    "\U0001F680-\U0001F6FF"      # transport & map
    "\U0001F1E0-\U0001F1FF"      # flags
    "\u2600-\u27BF"              # misc symbols + dingbats
    "\uFE00-\uFE0F"              # variation selectors
    "\u200D"                     # ZWJ
    "\u20E3"                     # combining enclosing keycap
    "]"
)

def clean_message(text):
    if not text: return text

    # ── 装饰/残留清理 ──
    text = re.sub(r"<[^>]+>", "", text)           # HTML tags
    text = re.sub(r"【([^】]*)】", r"\1", text)   # Markdown decorations
    text = re.sub(r"#([^#\s]+)#", r"\1", text)    # Markdown decorations
    text = re.sub(r"\[draft\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[ASR\]", "", text)
    text = re.sub(r"#todo", "", text)
    text = re.sub(r"<!--.*?-->", "", text)         # 缓存注释
    text = re.sub(r"<<<<\s*", "", text)            # 测试粘贴边界
    text = re.sub(r"\s*>>>>", "", text)
    text = re.sub(r"ENDEND", "", text)
    text = re.sub(r"（口述）", "", text)
    text = re.sub(r"\(口述\)", "", text)
    text = re.sub(r"help:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)                # Markdown code fences
    text = text.replace("\u3000", " ")             # 全角空格

    # ── 去重特定模式 ──
    text = re.sub(r"，,+", "，", text)
    text = re.sub(r"…+", "…", text)
    text = re.sub(r"嗯嗯+", "嗯", text)
    text = re.sub(r"呃呃+", "呃", text)
    text = re.sub(r"啊啊+", "啊", text)
    text = re.sub(r"(然后){2,}", "然后", text)

    # ── 清理停顿/口语词 ──
    for fw in FILLER_WORDS:
        if len(fw) >= 2:
            text = text.replace(fw, "")
    # 单字填词：仅移除句首/标点后的孤立出现
    singles = [fw for fw in FILLER_WORDS if len(fw) == 1]
    if singles:
        sc = "".join(re.escape(c) for c in singles)
        bc = r"\s\u3000\u2026\u3002\uff0c\uff01\uff1f\u3001\uff1a\uff1b\uff08\uff09\"'\-"
        pat = r"(^|[" + bc + r"])[" + sc + r"]+"
        text = re.sub(pat, r"\1", text)
    text = re.sub(r"…+", "…", text)

    # ── 移除无意义 emoji ──
    text = EMOJI_RE.sub("", text)

    # ── 标准化重复标点 ──
    text = re.sub(r"！{2,}", "！", text)
    text = re.sub(r"!{2,}", "！", text)
    text = re.sub(r"\？{2,}", "？", text)
    text = re.sub(r"\?{2,}", "？", text)
    text = re.sub(r"…{2,}", "…", text)
    text = re.sub(r"，{2,}", "，", text)
    text = re.sub(r"。{2,}", "。", text)
    # Remove wave dash decoration
    text = text.replace("～", "")

    # ── 移除句末语气助词（含CJK间孤立出现） ──
    for particle in ["嘛", "吧", "啦", "呢", "呀", "哈", "嘿", "哎", "唉"]:
        text = re.sub(rf"{particle}([！？。，…\s])", r"\1", text)
        text = re.sub(rf"{particle}$", "", text)
        # Also remove between CJK chars: "好的呢您" → "好的您"
        text = re.sub(rf"([\u4e00-\u9fff]){particle}([\u4e00-\u9fff])", r"\1\2", text)

    # ── 移除标点间的插入感叹 ──
    for interj in ["哈", "嘿", "哎", "唉"]:
        text = re.sub(rf"([，。！？\s]){interj}([，。！？\s])", r"\1\2", text)

    # ── 清理残留 ──
    text = re.sub(r"([，,])，+", r"\1", text)
    text = re.sub(r"([：:？，。\u3001])…+", r"\1", text)
    text = re.sub(r"\s…+", " ", text)
    text = text.lstrip("…，,\t\n\r ")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    return text


def mask_sensitive(text):
    masked = False
    # Phone
    new_text = re.sub(r"1[3-9]\d{9}", "[REDACTED]", text)
    if new_text != text: masked = True
    # Email
    new_text2 = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED]", new_text)
    if new_text2 != new_text: masked = True
    return new_text2, masked


def normalize_time(raw):
    if not raw: return ""
    raw = raw.strip()
    for fmt in ["%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M:%S","%Y/%m/%d %H:%M:%S",
                "%Y-%m-%d %H:%M","%Y/%m/%d %H:%M","%Y/%m/%-d %H:%M",
                "%Y-%-m-%-dT%H:%M:%S","%Y年%m月%d日 %H:%M:%S","%Y年%m月%d日 %H:%M"]:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError: continue
    return raw


def apply_typos(text):
    """Fix common typos."""
    for wrong, right in FIX_TYPOS.items():
        if wrong in text:
            text = text.replace(wrong, right)
    return text


def main():
    if not os.path.exists(INPUT):
        print(f"ERROR: {INPUT} not found")
        return
    with open(INPUT, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"Input: {len(rows)} rows")
    review = []
    seen = set()
    cleaned = []
    for i, row in enumerate(rows, start=2):
        sid = row.get("session_id","").strip()
        uid = row.get("user_id","").strip()
        role = row.get("role","").strip()
        msg = row.get("message","").strip()
        ts = row.get("created_at","").strip()
        if not msg:
            review.append(f"[DROP] empty msg | L{i} | {sid} {uid} {role}")
            continue
        if not uid:
            review.append(f"[MISSING_UID] L{i} | {sid} {role}")
            uid = "UNKNOWN"
        key = (sid, uid, role, msg)
        if key in seen:
            review.append(f"[DUP] L{i} | {sid} {uid}")
            continue
        seen.add(key)
        clean_msg = clean_message(msg)
        clean_msg = apply_typos(clean_msg)
        clean_msg, masked = mask_sensitive(clean_msg)
        if masked:
            review.append(f"[PII] L{i} | {sid} {uid}")
        norm_ts = normalize_time(ts)
        cleaned.append({"session_id":sid,"user_id":uid,"role":role,
                         "message":clean_msg,"created_at":norm_ts})
    cleaned.sort(key=lambda r: (r["session_id"], r["created_at"], r["role"]))
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["session_id","user_id","role","message","created_at"])
        w.writeheader(); w.writerows(cleaned)
    with open(REVIEW_LOG, "w", encoding="utf-8") as f:
        f.write("D3 Review Log\n" + "="*40 + "\n")
        for item in review: f.write(item + "\n")
    print(f"Output: {len(cleaned)} rows, {len(review)} review items")
    print(f"Files: {OUTPUT}, {REVIEW_LOG}")

if __name__ == "__main__":
    main()


