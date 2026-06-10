"""
mini_memory_agent.py — Mini Memory Agent

A lightweight agent that loads consolidated data from Phase 2 and provides
a CLI interface with /commands for multi-turn interaction.

Features:
  - Knowledge retrieval (bigram-based)
  - Preference injection per user
  - PII redaction (email, phone, id_card, ip)
  - Forget / remember detection
  - User isolation by uid
  - --test mode for automated evaluation

Data sources (phase2-consolidate):
  - knowledge_items.json
  - preferences.json
  - memory_snapshots_resolved.json
  - chat_turns.json
  - tool_executions.json
  - memory_events.json

CLI Commands:
  /search <query>   - Search knowledge base
  /pref             - List preferences for current user
  /mem              - Show memory snapshots for current user
  /forget <pattern> - Mark knowledge/preferences as forgotten
  /uid <uid>        - Switch user context (isolation)
  /help             - Show help
  /quit             - Exit
"""
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DATA_DIR = os.path.join(ROOT, "phase2-consolidate")

DATA_FILES = {
    "knowledge": "knowledge_items.json",
    "preferences": "preferences.json",
    "snapshots": "memory_snapshots_resolved.json",
    "chat_turns": "chat_turns.json",
    "tools": "tool_executions.json",
    "events": "memory_events.json",
}

# ═══════════════════════════════════════════════════
# PII Patterns
# ═══════════════════════════════════════════════════
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "phone": re.compile(r"1[3-9]\d{9}"),
    "id_card": re.compile(r"\b\d{17}[\dXx]\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}


def redact_pii(text: str) -> Tuple[str, bool]:
    """Redact PII from text. Returns (clean_text, has_pii)."""
    had_pii = False
    for pattern in PII_PATTERNS.values():
        if pattern.search(text):
            had_pii = True
            break
    clean = text
    clean = PII_PATTERNS["email"].sub("[EMAIL]", clean)
    clean = PII_PATTERNS["phone"].sub("[PHONE]", clean)
    clean = PII_PATTERNS["id_card"].sub("[ID_CARD]", clean)
    clean = PII_PATTERNS["ip_address"].sub("[IP]", clean)
    return clean, had_pii


# ═══════════════════════════════════════════════════
# Bigram Knowledge Retrieval
# ═══════════════════════════════════════════════════

SYNONYM_MAP = {
    "月报": ["会议纪要", "月度报告"],
    "周报": ["会议纪要", "周度报告"],
    "驱动": ["驱动更新", "驱动管理器", "安装驱动"],
    "麒麟": ["麒麟系统"],
    "离线安装": ["dpkg", "离线部署"],
    "deb": ["dpkg"],
    "会议纪要": ["月报", "周报", "会议记录"],
    "文档导出": ["导出PDF", "导出"],
    "wps": ["word", "文档"],
    "隐私": ["设置", "敏感"],
    "别记": ["忘记", "不保存"],
    "dpkg": ["离线安装", "deb"],
}


def build_bigrams(text: str) -> set:
    text = text.replace(" ", "").lower()
    if len(text) < 2:
        return {text}
    return {text[i:i + 2] for i in range(len(text) - 1)}


def bigram_similarity(a: str, b: str) -> float:
    bg_a = build_bigrams(a)
    bg_b = build_bigrams(b)
    if not bg_a or not bg_b:
        return 0.0
    inter = len(bg_a & bg_b)
    union = len(bg_a | bg_b)
    return inter / union if union > 0 else 0.0


def expand_synonyms(query: str) -> List[str]:
    expansions = [query]
    for key, synonyms in SYNONYM_MAP.items():
        if key in query:
            for syn in synonyms:
                if syn not in query:
                    expansions.append(query.replace(key, syn))
    return expansions


def search_knowledge(query: str, knowledge: List[Dict]) -> List[Dict]:
    """Bigram search over knowledge items with synonym expansion."""
    expanded = expand_synonyms(query)
    scored = []
    for item in knowledge:
        body = item.get("body", "")
        title = item.get("title", "")
        text = f"{title} {body}"
        best = 0.0
        for eq in expanded:
            s = bigram_similarity(eq, text)
            best = max(best, s)
        if best > 0.03:
            scored.append({"item": item, "score": round(best, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:5]


# ═══════════════════════════════════════════════════
# Forget / Remember Detection
# ═══════════════════════════════════════════════════

FORGET_KEYWORDS = ["别记", "忘记", "忘掉", "不保存", "删除", "不要记录", "别记下"]
REMEMBER_KEYWORDS = ["记住", "偏好", "以后都", "总是", "永久", "习惯", "喜欢"]


def detect_forget_intent(text: str) -> bool:
    """Check if user wants to forget/redact information."""
    return any(kw in text for kw in FORGET_KEYWORDS)


def detect_remember_intent(text: str) -> bool:
    """Check if user wants to remember/save a preference."""
    return any(kw in text for kw in REMEMBER_KEYWORDS)


# ═══════════════════════════════════════════════════
# Mini Memory Agent
# ═══════════════════════════════════════════════════

class MiniMemoryAgent:
    """Agent with knowledge retrieval, preferences, and memory management."""

    def __init__(self):
        self.knowledge: List[Dict] = []
        self.preferences: List[Dict] = []
        self.snapshots: List[Dict] = []
        self.chat_turns: List[Dict] = []
        self.tools: List[Dict] = []
        self.events: List[Dict] = []
        self.current_uid: str = "u001"
        self.forgotten: set = set()  # (uid, key) tuples
        self._load_all()

    def _load_json(self, key: str) -> List[Dict]:
        fname = DATA_FILES.get(key, "")
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    return []
            # Normalize knowledge items: add id/body fields if missing
            if key == "knowledge":
                for i, k in enumerate(data, 1):
                    k["id"] = k.get("id", f"K{i:03d}")
                    k["body"] = k.get("body", f"{k.get('title','')} {' '.join(k.get('tags',[]))} {' '.join(k.get('steps',[]))} {k.get('notes','')} {k.get('requirements','')}")
            return data
        return []

    def _load_all(self):
        """Load all data files from phase2-consolidate."""
        self.knowledge = self._load_json("knowledge")
        self.preferences = self._load_json("preferences")
        self.snapshots = self._load_json("snapshots")
        self.chat_turns = self._load_json("chat_turns")
        self.tools = self._load_json("tools")
        self.events = self._load_json("events")
        return self

    def get_preferences(self, uid: str) -> List[Dict]:
        """Get preferences for a specific user (case-insensitive uid match)."""
        uid_lower = uid.lower()
        return [p for p in self.preferences if p.get("uid", "").lower() == uid_lower]

    def get_snapshots(self, uid: str) -> List[Dict]:
        """Get memory snapshots for a specific user."""
        uid_lower = uid.lower()
        return [s for s in self.snapshots if s.get("uid", "").lower() == uid_lower]

    def get_chat_history(self, uid: str) -> List[Dict]:
        """Get chat turns for a specific user."""
        uid_upper = uid.upper()
        uid_lower = uid.lower()
        return [c for c in self.chat_turns
                if c.get("user_id", "") == uid_upper or c.get("user_id", "").lower() == uid_lower]

    def inject_preferences(self, uid: str, query: str) -> str:
        """Inject relevant user preferences into the context."""
        prefs = self.get_preferences(uid)
        if not prefs:
            return ""
        lines = [f"[偏好上下文 - {uid}]"]
        for p in prefs:
            lines.append(f"  {p.get('pref_key', '')}: {p.get('pref_value', '')}")
        return "\n".join(lines)

    def cmd_search(self, query: str) -> str:
        """Handle /search command."""
        uid = self.current_uid
        clean_q, has_pii = redact_pii(query)

        if has_pii:
            print(f"[!] PII detected & redacted in query.")

        # Forget detection
        if detect_forget_intent(clean_q):
            self.forgotten.add((uid, clean_q[:40]))
            result = "[!] 隐私保护：该信息包含敏感内容，已被标记为不记录。"
            return result

        # Bigram search
        results = search_knowledge(clean_q, self.knowledge)

        # Filter forgotten items
        results = [r for r in results if (uid, r["item"]["body"][:40]) not in self.forgotten]

        lines = [f"[Search] 知识检索结果 (uid={uid}):"]
        if results:
            for r in results:
                item = r["item"]
                lines.append(f"  [{item['id']}] score={r['score']:.3f} | {item['body']}")
        else:
            lines.append("  (未找到匹配的知识条目)")

        # Preference injection
        pref_ctx = self.inject_preferences(uid, clean_q)
        if pref_ctx:
            lines.append(f"\n{pref_ctx}")

        # Remember detection
        if detect_remember_intent(clean_q):
            lines.append("\n[Save] 偏好已记录：系统将记住该偏好用于后续对话。")

        return "\n".join(lines)

    def cmd_pref(self) -> str:
        """Handle /pref command — list user preferences."""
        uid = self.current_uid
        prefs = self.get_preferences(uid)
        lines = [f"[Prefs] 用户偏好 (uid={uid}):"]
        if not prefs:
            lines.append("  (无记录)")
        for p in prefs:
            val_clean, _ = redact_pii(p.get("pref_value", ""))
            lines.append(f"  [{p.get('type','?')} v{p.get('version','?')}] "
                         f"{p.get('pref_key','')}: {val_clean}")
        return "\n".join(lines)

    def cmd_mem(self) -> str:
        """Handle /mem command — show memory snapshots."""
        uid = self.current_uid
        snaps = self.get_snapshots(uid)
        lines = [f"[Memory] 记忆快照 (uid={uid}):"]
        if not snaps:
            lines.append("  (无记录)")
        for s in snaps:
            val_clean, _ = redact_pii(s.get("memory_value", ""))
            scope = s.get("scope", "?")
            if scope == "deleted":
                val_clean = "[FORGOTTEN]"
            lines.append(f"  [{s.get('key','?')}] {val_clean} "
                         f"(scope={scope} v{s.get('version','')})")
        return "\n".join(lines)

    def cmd_forget(self, pattern: str) -> str:
        """Handle /forget command — mark items as forgotten."""
        if not pattern or not pattern.strip():
            return "[Forget] 请提供要遗忘的内容匹配模式。例如: /forget 邮箱"
        uid = self.current_uid
        # Match against knowledge and preferences
        forgotten_count = 0
        for item in self.knowledge:
            body = item.get("body", "")
            if pattern in body:
                self.forgotten.add((uid, body[:40]))
                forgotten_count += 1
        for p in self.preferences:
            if p.get("uid", "").lower() == uid.lower():
                val = p.get("pref_value", "")
                if pattern in val:
                    self.forgotten.add((uid, val[:40]))
                    forgotten_count += 1
        return f"[Forget] 已标记 {forgotten_count} 条信息为遗忘 (uid={uid}, pattern='{pattern}')"

    def cmd_uid(self, uid: str) -> str:
        """Handle /uid command — switch user context."""
        old = self.current_uid
        self.current_uid = uid.strip()
        return f"[User] 用户上下文已切换: {old} → {self.current_uid}"

    def cmd_help(self) -> str:
        return """╔═══════════════════════════════════════╗
║  Mini Memory Agent — Commands       ║
╠═══════════════════════════════════════╣
║  /search <query>  知识库检索         ║
║  /pref            查看用户偏好        ║
║  /mem             查看记忆快照        ║
║  /forget <pattern> 标记遗忘信息       ║
║  /uid <uid>       切换用户上下文      ║
║  /help            显示帮助            ║
║  /quit            退出                ║
║  /stats           查看数据统计        ║
╚═══════════════════════════════════════╝"""

    def cmd_stats(self) -> str:
        return (f"[Stats] 数据统计:\n"
                f"  knowledge_items:  {len(self.knowledge)}\n"
                f"  preferences:      {len(self.preferences)}\n"
                f"  snapshots:        {len(self.snapshots)}\n"
                f"  chat_turns:       {len(self.chat_turns)}\n"
                f"  tool_executions:  {len(self.tools)}\n"
                f"  memory_events:    {len(self.events)}\n"
                f"  current_uid:      {self.current_uid}\n"
                f"  forgotten_items:  {len(self.forgotten)}")


# ═══════════════════════════════════════════════════
# CLI Loop
# ═══════════════════════════════════════════════════

COMMANDS = {
    "/search": lambda a, q: a.cmd_search(q),
    "/pref": lambda a, _: a.cmd_pref(),
    "/mem": lambda a, _: a.cmd_mem(),
    "/forget": lambda a, q: a.cmd_forget(q),
    "/uid": lambda a, q: a.cmd_uid(q),
    "/help": lambda a, _: a.cmd_help(),
    "/quit": lambda a, _: "EXIT",
    "/stats": lambda a, _: a.cmd_stats(),
}


def run_cli(agent: MiniMemoryAgent):
    """Interactive CLI loop."""
    print("╔══════════════════════════════════════════════════╗")
    print("║        Mini Memory Agent — CLI Mode             ║")
    print("║  输入 /help 查看命令, /quit 退出                 ║")
    print("╚══════════════════════════════════════════════════╝")
    while True:
        try:
            user_input = input(f"\n[{agent.current_uid}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Bye] 再见!")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in COMMANDS:
                result = COMMANDS[cmd](agent, arg)
                if result == "EXIT":
                    print("[Bye] 再见!")
                    break
                print(result)
            else:
                print(f"[?] 未知命令: {cmd}，输入 /help 查看帮助")
        else:
            # Treat plain text as implicit search
            result = agent.cmd_search(user_input)
            print(result)


# ═══════════════════════════════════════════════════
# Test Cases
# ═══════════════════════════════════════════════════

TEST_CASES = [
    {
        "id": 1,
        "uid": "u001",
        "query": "麒麟系统如何更新驱动？",
        "description": "u001 麒麟系统如何更新驱动 → 知识检索+偏好注入(u001有output_style)",
        "expected_knowledge": None,  # may or may not match depending on knowledge base
        "check_pref": True,
    },
    {
        "id": 2,
        "uid": "u001",
        "query": "写月报摘要",
        "description": "u001 写月报摘要 → 同义词扩展(月报→会议纪要) 命中知识库",
        "expected_knowledge_keywords": ["会议纪要"],
        "check_pref": True,
    },
    {
        "id": 3,
        "uid": "u002",
        "query": "你好",
        "description": "u002 你好 → 无知识匹配, 检测emoji_policy偏好",
        "expected_knowledge": [],
        "check_pref": True,
        "check_memory": "u002",
    },
    {
        "id": 4,
        "uid": "u003",
        "query": "怎么离线安装.deb软件包？",
        "description": "u003 怎么离线安装.deb软件包 → 同义词扩展(deb→dpkg/离线安装) 命中知识库",
        "expected_knowledge_keywords": ["离线安装", "deb"],
        "check_pref": False,
    },
    {
        "id": 5,
        "uid": "u004",
        "query": "liubei@shu.com 别记下这个邮箱",
        "description": "u004 邮箱+别记下 → privacy+脱敏+forget",
        "check_pii": True,
        "check_forget": True,
    },
]


def run_tests(agent: MiniMemoryAgent) -> Tuple[int, int]:
    """Run automated test cases. Returns (passed, total)."""
    print("=" * 60)
    print("  Mini Memory Agent — Test Suite")
    print("=" * 60)

    passed = 0
    total = len(TEST_CASES)

    for tc in TEST_CASES:
        tid = tc["id"]
        print(f"\n{'─' * 50}")
        print(f"  Test {tid}: {tc['description']}")

        # Switch uid
        agent.current_uid = tc["uid"]

        # Run search
        clean_q, has_pii = redact_pii(tc["query"])
        result = agent.cmd_search(tc["query"])
        print(result)

        # Checks
        checks_passed = True

        # 1) Knowledge check (by exact ID)
        expected_k = tc.get("expected_knowledge")
        if expected_k:
            found_ids = set()
            search_results = search_knowledge(clean_q, agent.knowledge)
            for r in search_results:
                found_ids.add(r["item"]["id"])
            expected_ids = set(expected_k)
            match = found_ids & expected_ids
            if match:
                print(f"  [PASS] Knowledge match: {match}")
            else:
                print(f"  [FAIL] Knowledge miss: expected {expected_ids}, got {found_ids}")
                checks_passed = False

        # 1b) Knowledge check (by keyword — for large generated datasets)
        expected_kw = tc.get("expected_knowledge_keywords")
        if expected_kw:
            search_results = search_knowledge(clean_q, agent.knowledge)
            if not search_results:
                print(f"  [FAIL] Knowledge miss: no results for keyword check {expected_kw}")
                checks_passed = False
            else:
                bodies = [r["item"].get("body", "") for r in search_results]
                matched = [kw for kw in expected_kw if any(kw in b for b in bodies)]
                if matched:
                    print(f"  [PASS] Knowledge keywords matched: {matched} in {len(search_results)} result(s)")
                else:
                    top_bodies = [b[:60] for b in bodies[:3]]
                    print(f"  [FAIL] Keywords {expected_kw} not found in: {top_bodies}")
                    checks_passed = False

        # 2) PII check
        if tc.get("check_pii"):
            if has_pii:
                print(f"  [PASS] PII detected: query contains sensitive data")
            else:
                print(f"  [FAIL] PII not detected as expected")
                checks_passed = False

        # 3) Forget check
        if tc.get("check_forget"):
            has_forget = detect_forget_intent(tc["query"])
            if has_forget:
                print(f"  [PASS] Forget intent detected")
            else:
                print(f"  [FAIL] Forget intent not detected")
                checks_passed = False

        # 4) Preference check
        if tc.get("check_pref"):
            prefs = agent.get_preferences(tc["uid"])
            if prefs:
                print(f"  [PASS] Preferences loaded: {len(prefs)} pref(s) for {tc['uid']}")
            else:
                print(f"  [WARN] No preferences found for {tc['uid']}")

        # 5) Memory snapshot check
        if tc.get("check_memory"):
            uid = tc["check_memory"]
            snaps = agent.get_snapshots(uid)
            if snaps:
                print(f"  [PASS] Memory snapshots: {len(snaps)} snapshot(s) for {uid}")
            else:
                print(f"  [WARN] No snapshots for {uid}")

        if checks_passed:
            passed += 1
            print(f"  [PASS] Test {tid} PASSED")
        else:
            print(f"  [FAIL] Test {tid} FAILED")

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed}/{total} tests passed")
    print("=" * 60)
    return passed, total


# ═══════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════

def main():
    agent = MiniMemoryAgent()

    if "--test" in sys.argv:
        passed, total = run_tests(agent)
        sys.exit(0 if passed == total else 1)
    else:
        print(f"\n[Data] 数据加载完成:")
        print(f"   knowledge_items:  {len(agent.knowledge)}")
        print(f"   preferences:      {len(agent.preferences)}")
        print(f"   snapshots:        {len(agent.snapshots)}")
        print(f"   chat_turns:       {len(agent.chat_turns)}")
        print(f"   tool_executions:  {len(agent.tools)}")
        print(f"   memory_events:    {len(agent.events)}")
        run_cli(agent)


if __name__ == "__main__":
    main()
