"""
workflow.py — LangGraph 3-Node Workflow (Pure Python)

Architecture (per spec: 2-3 nodes):
  ┌────────────────────────────────────────────────────────┐
  │  [classify] → [retrieve / chat] → [output]             │
  │      意图分类       知识检索/聊天         格式化输出      │
  └────────────────────────────────────────────────────────┘

Node 1 (classify): PII过滤 + 意图分类 → knowledge_query | casual_chat | memory_query
Node 2 (retrieve / chat): 知识检索(bigram+同义词) / 普通聊天回复 / 记忆查询
Node 3 (output): 格式化最终输出

Knowledge source: phase2-consolidate/knowledge_items.json (D4 清洗结果)
"""
import json
import os
import re
from typing import Any, Dict, List, Tuple

# ═══════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
KNOWLEDGE_PATH = os.path.join(ROOT, "phase2-consolidate", "knowledge_items.json")

# ═══════════════════════════════════════════════════
# PII Patterns (集成在 Node 1 classify 中)
# ═══════════════════════════════════════════════════
PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "phone": re.compile(r"1[3-9]\d{9}"),
    "id_card": re.compile(r"\b\d{17}[\dXx]\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

# ═══════════════════════════════════════════════════
# Synonym Map (同义词扩展)
# ═══════════════════════════════════════════════════
SYNONYM_MAP = {
    "月报": ["会议纪要", "月度报告"],
    "周报": ["会议纪要", "周度报告"],
    "会议纪要": ["月报", "周报", "会议记录"],
    "驱动": ["驱动更新", "驱动安装"],
    "麒麟": ["麒麟系统"],
    "离线安装": ["dpkg", "离线部署"],
    "deb": ["dpkg"],
    "dpkg": ["deb", "离线安装"],
}

# ═══════════════════════════════════════════════════
# Intent Keywords
# ═══════════════════════════════════════════════════
KNOWLEDGE_KW = ["怎么", "如何", "怎样", "安装", "配置", "驱动", "更新",
                "导出", "麒麟", "deb", "dpkg", "软件", "系统",
                "离线", "月报", "周报", "问题"]
CASUAL_KW = ["你好", "谢谢", "再见", "嗨", "hello", "hi", "bye"]
MEMORY_KW = ["记住", "偏好", "记忆", "永久", "总是", "以后", "不需要",
             "禁用", "启用", "别记", "忘记", "别用", "以后都"]

# ═══════════════════════════════════════════════════
# Bigram Utilities
# ═══════════════════════════════════════════════════

def build_bigrams(text: str) -> set:
    text = text.replace(" ", "").lower()
    if len(text) < 2:
        return {text}
    return {text[i:i + 2] for i in range(len(text) - 1)}


def bigram_similarity(a: str, b: str) -> float:
    bg_a, bg_b = build_bigrams(a), build_bigrams(b)
    if not bg_a or not bg_b:
        return 0.0
    return len(bg_a & bg_b) / len(bg_a | bg_b)


def expand_synonyms(query: str) -> List[str]:
    expansions = [query]
    for key, synonyms in SYNONYM_MAP.items():
        if key in query:
            for syn in synonyms:
                if syn not in query:
                    expansions.append(query.replace(key, syn))
    return expansions


def search_knowledge(query: str, knowledge: List[Dict]) -> List[Dict]:
    expanded = expand_synonyms(query)
    scored = []
    for item in knowledge:
        body = item.get("body", "")
        title = item.get("title", "")
        text = f"{title} {body}"
        best = max(bigram_similarity(eq, text) for eq in expanded)
        if best > 0.03:
            scored.append({"item": item, "score": round(best, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:3]


# ═══════════════════════════════════════════════════
# Node 1: classify (PII过滤 + 意图分类)
# ═══════════════════════════════════════════════════

def node_classify(state: Dict) -> Dict:
    """合并 PII 检测 + 意图分类为一个节点"""
    query = state.get("query", "")

    # 1) PII detection
    detections = []
    clean = query
    for pii_type, pattern in PII_PATTERNS.items():
        for m in pattern.finditer(query):
            detections.append({"type": pii_type, "matched": m.group()})
        clean = pattern.sub(f"[{pii_type.upper()}]", clean)

    state["clean_query"] = clean
    state["pii_detections"] = detections
    state["has_pii"] = len(detections) > 0

    if state["has_pii"]:
        print(f"  [PII] Detected: {', '.join(d['type'] for d in detections)}")

    # 2) Intent classification (3-way routing per spec)
    # memory_query first (forget/remember keywords)
    for kw in MEMORY_KW:
        if kw in clean:
            state["intent"] = "memory_query"
            print(f"  [Intent] → memory_query")
            return state

    # casual_chat
    qs = clean.strip()
    if qs in CASUAL_KW or (len(qs) <= 3 and qs in CASUAL_KW):
        state["intent"] = "casual_chat"
        print(f"  [Intent] → casual_chat")
        return state

    # knowledge_query (default)
    state["intent"] = "knowledge_query"
    print(f"  [Intent] → knowledge_query")
    return state


# ═══════════════════════════════════════════════════
# Node 2a: retrieve — 知识检索
# ═══════════════════════════════════════════════════

def node_retrieve(state: Dict) -> Dict:
    query = state.get("clean_query", state.get("query", ""))
    knowledge = state.get("_knowledge_items", [])
    results = search_knowledge(query, knowledge)
    state["retrieved"] = results
    if results:
        print(f"  [Retrieve] Top {len(results)} match(es):")
        for r in results:
            print(f"    {r['item']['id']} [score={r['score']}] {r['item']['body'][:60]}")
    else:
        print(f"  [Retrieve] No match")
    return state


# ═══════════════════════════════════════════════════
# Node 2b: chat — 普通聊天
# ═══════════════════════════════════════════════════

REPLIES = {
    "你好": "你好！有什么可以帮助你的？",
    "谢谢": "不客气！",
    "再见": "再见，祝你生活愉快！",
    "嗨": "嗨！请问有什么需要？",
}

def node_chat(state: Dict) -> Dict:
    query = state.get("clean_query", "").strip()
    state["chat_reply"] = REPLIES.get(query, "你好，我是麒麟 Agent 助手，专注 OS 相关问题。")
    print(f"  [Chat] {state['chat_reply']}")
    return state


# ═══════════════════════════════════════════════════
# Node 2c: memory — 记忆查询
# ═══════════════════════════════════════════════════

def node_memory(state: Dict) -> Dict:
    query = state.get("clean_query", "")
    actions = [
        ("忘记" in query or "别记" in query, "forget", "系统已记录：相关内容将不被保存到长期记忆中。"),
        ("禁用" in query or "不需要" in query or "别用" in query, "disable", "系统已记录：该偏好已禁用。"),
        ("启用" in query, "enable", "系统已记录：该偏好已启用。"),
        ("记住" in query or "偏好" in query, "remember", "系统已记录：该偏好已保存到长期记忆中。"),
    ]
    for cond, action, msg in actions:
        if cond:
            state["memory_action"] = action
            state["memory_response"] = msg
            print(f"  [Memory] {action}: {msg}")
            return state
    state["memory_action"] = "query"
    state["memory_response"] = "未找到相关记忆记录。"
    return state


# ═══════════════════════════════════════════════════
# Node 3: output — 格式化输出
# ═══════════════════════════════════════════════════

def node_output(state: Dict) -> Dict:
    print(f"\n{'─' * 50}")
    print(f"Query:  {state.get('query', '')}")
    print(f"Intent: {state.get('intent', '?')}")
    if state.get("has_pii"):
        print(f"PII:    Filtered ({len(state.get('pii_detections', []))} patterns)")

    intent = state.get("intent", "")
    if intent == "knowledge_query":
        retrieved = state.get("retrieved", [])
        state["final_output"] = "\n".join(
            f"[{r['item']['id']}] {r['item']['body']}" for r in retrieved
        ) if retrieved else "未找到相关知识条目。"
    elif intent == "casual_chat":
        state["final_output"] = state.get("chat_reply", "")
    elif intent == "memory_query":
        state["final_output"] = state.get("memory_response", "")

    print(f"Output: {state['final_output']}")
    print(f"{'─' * 50}")
    return state


# ═══════════════════════════════════════════════════
# StateGraph Polyfill
# ═══════════════════════════════════════════════════

class GraphNode:
    def __init__(self, name, func): self.name = name; self.func = func
    def run(self, state): return self.func(state)


class StateGraph:
    def __init__(self, initial_state):
        self.nodes = {}
        self.entry = None
        self.conditions = {}
        self.routes = {}
        self.edges = {}
        self.finish = None
        self.initial_state = initial_state

    def add_node(self, name, func):
        self.nodes[name] = GraphNode(name, func); return self
    def set_entry_point(self, name):
        self.entry = name; return self
    def add_edge(self, frm, to):
        self.edges[frm] = to; return self
    def add_conditional_edges(self, frm, cond, routes):
        self.conditions[frm] = cond; self.routes[frm] = routes; return self
    def set_finish_point(self, name):
        self.finish = name; return self
    def compile(self):
        return CompiledGraph(self)


class CompiledGraph:
    def __init__(self, graph): self.graph = graph
    def invoke(self, state=None):
        state = state or self.graph.initial_state
        current = self.graph.entry
        while current:
            node = self.graph.nodes.get(current)
            if not node: break
            state = node.run(state)
            state["_last"] = current
            # conditional edges
            if current in self.graph.conditions:
                result = self.graph.conditions[current](state)
                current = self.graph.routes[current].get(result, "")
                if current: continue
            # direct edge
            current = self.graph.edges.get(current)
        return state


# ═══════════════════════════════════════════════════
# Build Workflow
# ═══════════════════════════════════════════════════

def load_knowledge():
    items = []
    if os.path.exists(KNOWLEDGE_PATH):
        with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for i, k in enumerate(raw, 1):
            k["id"] = f"K{i:03d}"
            k["body"] = (f"{k.get('title','')} "
                         f"{' '.join(k.get('tags',[]))} "
                         f"{' '.join(k.get('steps',[]))} "
                         f"{k.get('notes','')} "
                         f"{k.get('requirements','')}")
            items.append(k)
    return items


def build_workflow():
    wf = StateGraph({"query": "", "_knowledge_items": load_knowledge()})

    # 3 nodes per spec
    wf.add_node("classify", node_classify)
    wf.add_node("retrieve", node_retrieve)
    wf.add_node("chat", node_chat)
    wf.add_node("memory", node_memory)
    wf.add_node("output", node_output)

    wf.set_entry_point("classify")
    wf.add_conditional_edges(
        "classify",
        lambda s: s.get("intent", "knowledge_query"),
        {"knowledge_query": "retrieve",
         "casual_chat": "chat",
         "memory_query": "memory"}
    )
    wf.add_edge("retrieve", "output")
    wf.add_edge("chat", "output")
    wf.add_edge("memory", "output")
    wf.set_finish_point("output")
    return wf.compile()


# ═══════════════════════════════════════════════════
# Demo (per D08 spec — knowledge from own D4 results)
# ═══════════════════════════════════════════════════

DEMO = [
    ("麒麟系统如何更新驱动？",    "knowledge_query"),
    ("怎么写月报摘要？",          "knowledge_query → K002 synonym expanded"),
    ("你好",                     "casual_chat"),
    ("怎么离线安装.deb软件包？",  "knowledge_query → K001"),
    ("liubei@shu.com 帮我导出PDF", "knowledge_query + PII(email)"),
    ("以后回复别用emoji",         "memory_query → disable"),
    ("记住我喜欢详细输出带表格",  "memory_query → remember"),
    ("192.168.1.100 连不上了",    "knowledge_query + PII(ip)"),
    ("帮我查13812345678",         "knowledge_query + PII(phone)"),
]


def main():
    print("=" * 60)
    print("  LangGraph 3-Node Workflow (D08)")
    print("  Knowledge: phase2-consolidate/knowledge_items.json")
    print("  Per spec: classify → retrieve/chat → output")
    print("=" * 60)

    wf = build_workflow()
    knowledge = load_knowledge()
    print(f"\nLoaded {len(knowledge)} knowledge item(s):")
    for k in knowledge:
        print(f"  {k['id']}: {k['body'][:80]}...")

    for i, (q, expected) in enumerate(DEMO, 1):
        print(f"\n{'█' * 50}")
        print(f"  [{i}/{len(DEMO)}] Expected: {expected}")
        wf.invoke({"query": q, "_knowledge_items": knowledge})

    print(f"\n{'=' * 60}")
    print(f"  Demo Complete — {len(DEMO)} queries, 3-node workflow")
    print("=" * 60)


if __name__ == "__main__":
    main()
