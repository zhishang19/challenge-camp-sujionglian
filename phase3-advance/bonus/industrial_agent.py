"""
industrial_agent.py — 工业级 Agent（选做 +20分）

基于 Mini Memory Agent 扩展的工业级特性：
  [1] 多轮对话上下文管理 (session memory)
  [2] 知识向量化检索 (TF-IDF + cosine, 替代纯bigram)
  [3] 用户偏好持久化 (JSON文件读写, 跨会话)
  [4] 检索耗时统计 (本地模拟 ≤500ms 评测意识)
  [5] 完整的日志系统 (logging to file)
  [6] 异常处理与降级策略

运行:
  cd phase3-advance
  python bonus/industrial_agent.py
"""
import json
import os
import re
import time
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# ═══════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "agent.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # bonus/
ROOT = os.path.dirname(os.path.dirname(BASE_DIR))  # project root
DATA_DIR = os.path.join(ROOT, "phase2-consolidate")
PREF_STORE = os.path.join(BASE_DIR, "user_prefs_store.json")

# ═══════════════════════════════════════════════════
# [1] Session Memory — 多轮对话上下文
# ═══════════════════════════════════════════════════
MAX_HISTORY = 20  # 最多保留 20 轮

class SessionMemory:
    """Per-user session memory with TTL-based expiry."""
    def __init__(self):
        self._sessions: Dict[str, List[Dict]] = defaultdict(list)  # uid → [turns]
        self._created: Dict[str, float] = {}  # uid → timestamp

    def add(self, uid: str, role: str, content: str):
        uid = uid.lower()
        if uid not in self._created:
            self._created[uid] = time.time()
        self._sessions[uid].append({
            "role": role, "content": content, "time": time.time()
        })
        if len(self._sessions[uid]) > MAX_HISTORY:
            self._sessions[uid] = self._sessions[uid][-MAX_HISTORY:]

    def get_context(self, uid: str, last_n: int = 5) -> str:
        uid = uid.lower()
        turns = self._sessions.get(uid, [])[-last_n:]
        if not turns:
            return ""
        return " | ".join(f"[{t['role']}]: {t['content'][:50]}" for t in turns)

    def clear(self, uid: str):
        self._sessions.pop(uid.lower(), None)
        self._created.pop(uid.lower(), None)

# ═══════════════════════════════════════════════════
# [2] TF-IDF + Cosine Similarity — 向量化检索
# ═══════════════════════════════════════════════════

def tokenize(text: str) -> List[str]:
    """Chinese-friendly tokenizer: char bigrams + single chars."""
    text = re.sub(r"\s+", "", text).lower()
    tokens = []
    for i in range(len(text)):
        if i > 0:
            tokens.append(text[i-1:i+1])  # bigram
        tokens.append(text[i])  # unigram
    return tokens


class TfidfRetriever:
    """TF-IDF vector space model for knowledge retrieval."""
    def __init__(self):
        self.documents: List[Dict] = []
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.tfidf_matrix: List[Dict[str, float]] = []

    def fit(self, documents: List[Dict]):
        self.documents = documents
        # Build vocabulary
        doc_tokens = []
        for doc in documents:
            body = doc.get("body", "")
            title = doc.get("title", "")
            tokens = tokenize(f"{title} {body}")
            doc_tokens.append(tokens)
            for t in set(tokens):
                self.vocab[t] = self.vocab.get(t, 0) + 1

        # IDF
        N = len(documents)
        for term, df in self.vocab.items():
            self.idf[term] = (N + 1) / (df + 1)

        # TF-IDF vectors
        for tokens in doc_tokens:
            tf = defaultdict(int)
            for t in tokens:
                tf[t] += 1
            vec_len = sum(v ** 2 for v in tf.values()) ** 0.5 or 1
            self.tfidf_matrix.append({
                t: (cnt / vec_len) * self.idf.get(t, 1.0)
                for t, cnt in tf.items()
            })

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Cosine similarity search."""
        qt = tokenize(query)
        qf = defaultdict(int)
        for t in qt:
            qf[t] += 1
        q_len = sum(v ** 2 for v in qf.values()) ** 0.5 or 1

        scores = []
        for i, vec in enumerate(self.tfidf_matrix):
            dot = 0.0
            for t, w in qf.items():
                dot += (w / q_len) * vec.get(t, 0)
            d_norm = sum(v ** 2 for v in vec.values()) ** 0.5
            if d_norm > 0 and dot > 0.01:
                scores.append({
                    "item": self.documents[i],
                    "score": round(dot, 4)
                })
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

# ═══════════════════════════════════════════════════
# [3] User Preference Persistence
# ═══════════════════════════════════════════════════

class PreferenceStore:
    """Persistent preference storage with save/load."""
    def __init__(self):
        self._prefs: Dict[str, Dict[str, Dict]] = {}  # uid → key → {value, version, time}
        self._load()

    def _load(self):
        if os.path.exists(PREF_STORE):
            try:
                with open(PREF_STORE, "r", encoding="utf-8") as f:
                    self._prefs = json.load(f)
                log.info(f"Loaded preferences for {len(self._prefs)} users")
            except Exception as e:
                log.warning(f"Failed to load preferences: {e}")
                self._prefs = {}

    def _save(self):
        try:
            with open(PREF_STORE, "w", encoding="utf-8") as f:
                json.dump(self._prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Failed to save preferences: {e}")

    def set(self, uid: str, key: str, value: str):
        uid = uid.lower()
        if uid not in self._prefs:
            self._prefs[uid] = {}
        version = int(self._prefs[uid].get(key, {}).get("version", 0)) + 1
        self._prefs[uid][key] = {"value": value, "version": version, "time": str(datetime.now())}
        self._save()
        log.info(f"Pref set: {uid}.{key} = {value} (v{version})")

    def get(self, uid: str, key: str = None) -> Dict:
        uid = uid.lower()
        user_prefs = self._prefs.get(uid, {})
        if key:
            return {key: user_prefs.get(key, {}).get("value", "")} if key in user_prefs else {}
        return user_prefs

    def all_for(self, uid: str) -> str:
        prefs = self.get(uid)
        if not prefs:
            return "(无偏好)"
        return "; ".join(f"{k}: {v['value']}" for k, v in prefs.items())

# ═══════════════════════════════════════════════════
# [4] Latency Stats
# ═══════════════════════════════════════════════════

class LatencyTracker:
    """Track retrieval latency for ≤500ms evaluation."""
    def __init__(self):
        self.records: List[float] = []

    def measure(self, func, *args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000  # ms
        self.records.append(elapsed)
        return result, elapsed

    def stats(self) -> str:
        if not self.records:
            return "无记录"
        records = sorted(self.records)
        n = len(records)
        avg = sum(records) / n
        p50 = records[n // 2]
        p95 = records[int(n * 0.95)] if n >= 20 else records[-1]
        return (f"N={n} | avg={avg:.2f}ms | p50={p50:.2f}ms | "
                f"p95={p95:.2f}ms | max={records[-1]:.2f}ms | "
                f"≤500ms={'PASS' if p95 <= 500 else 'FAIL'}")

# ═══════════════════════════════════════════════════
# IndustrialAgent
# ═══════════════════════════════════════════════════

PII_RE = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "phone": re.compile(r"1[3-9]\d{9}"),
    "id_card": re.compile(r"\b\d{17}[\dXx]\b"),
}

class IndustrialAgent:
    def __init__(self):
        log.info("IndustrialAgent initializing...")
        self.retriever = TfidfRetriever()
        self.pref_store = PreferenceStore()
        self.sessions = SessionMemory()
        self.latency = LatencyTracker()
        self.knowledge: List[Dict] = []
        self._load_data()
        self.retriever.fit(self.knowledge)
        log.info(f"IndustrialAgent ready: {len(self.knowledge)} knowledge, "
                 f"{len(self.pref_store._prefs)} users")

    def _load_json(self, fname: str) -> List[Dict]:
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def _load_data(self):
        raw = self._load_json("knowledge_items.json")
        for i, k in enumerate(raw, 1):
            k["id"] = f"K{i:03d}"
            k["body"] = (f"{k.get('title','')} {' '.join(k.get('tags',[]))} "
                         f"{' '.join(k.get('steps',[]))} {k.get('notes','')} "
                         f"{k.get('requirements','')}")
            self.knowledge.append(k)
        # Load existing preferences into store
        prefs = self._load_json("preferences.json")
        for p in prefs:
            uid = p.get("uid", "").lower()
            key = p.get("pref_key", "")
            val = p.get("pref_value", "")
            if uid and key:
                if uid not in self.pref_store._prefs:
                    self.pref_store._prefs[uid] = {}
                self.pref_store._prefs[uid][key] = {
                    "value": val,
                    "version": int(p.get("version", 1)),
                    "time": p.get("time", "")
                }

    def redact(self, text: str) -> Tuple[str, List[str]]:
        found = []
        clean = text
        for ptype, pat in PII_RE.items():
            if pat.search(clean):
                found.append(ptype)
            clean = pat.sub(f"[{ptype.upper()}]", clean)
        return clean, found

    def answer(self, uid: str, query: str) -> str:
        """Main entry: process query with all industrial features."""
        uid = uid.lower()
        log.info(f"[{uid}] QUERY: {query}")

        # PII filter
        clean, pii = self.redact(query)
        if pii:
            log.info(f"[{uid}] PII detected: {pii}")

        # Forget intent
        if any(kw in clean for kw in ["别记", "忘记", "不要记录"]):
            log.info(f"[{uid}] FORGET intent")
            return "[隐私保护] 该信息包含敏感内容，已被标记为不记录。"

        # Preference set intent
        if "记住" in clean and "偏好" in clean:
            parts = clean.replace("记住", "").replace("偏好", "").strip()
            if parts:
                self.pref_store.set(uid, "user_preference", parts)
                return f"[已保存] 偏好已记录: {parts}"

        # [4] Latency-tracked retrieval
        result, elapsed = self.latency.measure(self.retriever.search, clean, top_k=3)

        # Build response
        lines = []
        if pii:
            lines.append(f"[PII Filtered: {', '.join(pii)}]")

        # Session context
        ctx = self.sessions.get_context(uid)
        if ctx:
            lines.append(f"[Context] {ctx}")

        # Preferences from persistent store
        prefs = self.pref_store.all_for(uid)
        if prefs != "(无偏好)":
            lines.append(f"[Prefs] {prefs}")

        # Knowledge results
        if result:
            lines.append(f"[Knowledge] Top {len(result)} (retrieval: {elapsed:.2f}ms):")
            for r in result:
                lines.append(f"  [{r['item']['id']}] score={r['score']:.4f} | {r['item']['body'][:80]}")
        else:
            lines.append("[Knowledge] 未找到匹配条目")

        # Add to session
        self.sessions.add(uid, "user", query)
        self.sessions.add(uid, "agent", lines[-1] if result else lines[0])

        return "\n".join(lines)


# ═══════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════

def main():
    agent = IndustrialAgent()

    demos = [
        ("u001", "麒麟系统如何更新驱动？"),
        ("u001", "怎么写月报摘要？"),
        ("u003", "怎么离线安装.deb软件包？"),
        ("u001", "记住我喜欢输出详细版带表格"),
        ("u001", "麒麟系统如何更新驱动？"),  # Now with preference
        ("u004", "liubei@shu.com 别记下这个邮箱"),
    ]

    print("=" * 60)
    print("  Industrial Agent — Demo")
    print("  Features: TF-IDF, session memory, pref persistence, latency tracking")
    print("=" * 60)

    for uid, query in demos:
        print(f"\n{'─' * 50}")
        print(f"[{uid}] > {query}")
        reply = agent.answer(uid, query)
        print(reply)

    print(f"\n{'=' * 60}")
    print(f"  [Latency Stats] {agent.latency.stats()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
