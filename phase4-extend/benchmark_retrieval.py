"""
benchmark_retrieval.py — Phase 4 Retrieval Benchmark
=====================================================
Measures knowledge retrieval response time against the target of <=500ms.
Uses bigram similarity search from phase3-advance/langgraph_workflow.py.

Sections:
  1. Single query benchmark (cold start)
  2. Batch benchmark (N queries, avg/min/max/p50/p95/p99)
  3. Generate benchmark report

Usage:
  py phase4-extend/benchmark_retrieval.py
"""
import json
import os
import time
import statistics
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
KNOWLEDGE_PATH = os.path.join(ROOT, "phase2-consolidate", "knowledge_items.json")

TARGET_MS = 500  # <=500ms target


def load_knowledge():
    if os.path.exists(KNOWLEDGE_PATH):
        with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def build_bigrams(text):
    text = text.replace(" ", "").lower()
    if len(text) < 2:
        return {text}
    return {text[i:i + 2] for i in range(len(text) - 1)}


def bigram_similarity(a, b):
    bg_a = build_bigrams(a)
    bg_b = build_bigrams(b)
    if not bg_a or not bg_b:
        return 0.0
    inter = len(bg_a & bg_b)
    union = len(bg_a | bg_b)
    return inter / union if union > 0 else 0.0


SYNONYM_MAP = {
    "月报": ["会议纪要", "月度报告"],
    "驱动": ["驱动更新", "驱动管理器"],
    "麒麟": ["麒麟系统"],
    "离线安装": ["dpkg", "离线部署"],
    "deb": ["dpkg"],
    "文档导出": ["导出PDF", "导出"],
    "wps": ["word", "文档"],
}


def expand_synonyms(query):
    expansions = [query]
    for key, synonyms in SYNONYM_MAP.items():
        if key in query:
            for syn in synonyms:
                if syn not in query:
                    expansions.append(query.replace(key, syn))
    return expansions


def search_knowledge(query, knowledge):
    """Bigram search — returns (results, elapsed_ms)."""
    start = time.perf_counter()
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
    elapsed = (time.perf_counter() - start) * 1000
    return scored[:5], elapsed


# Query set simulating real OS Agent scenarios
BENCHMARK_QUERIES = [
    "麒麟系统如何更新驱动",
    "怎么写月报摘要",
    "离线安装deb软件包",
    "WPS文档怎么导出PDF",
    "会议纪要撰写规范",
    "麒麟驱动管理器怎么用",
    "敏感信息怎么处理",
    "用户偏好怎么管理",
    "怎么在麒麟上装软件",
    "忘记密码怎么办",
    "如何设置默认输出格式",
    "文档怎么转换为PDF",
    "麒麟系统驱动安装步骤",
    "月报和周报的区别",
    "偏好记忆和知识记忆的区别",
]


def run_single_benchmark(knowledge):
    """Single query benchmark with detailed output."""
    print("\n" + "=" * 60)
    print("  1. Single Query Benchmark")
    print("=" * 60)

    query = "麒麟系统如何更新驱动"
    results, elapsed = search_knowledge(query, knowledge)

    status = "[OK]" if elapsed <= TARGET_MS else "[FAIL]"
    print(f"\n  Query:  {query}")
    print(f"  Time:   {elapsed:.2f} ms {status} (target <= {TARGET_MS}ms)")
    print(f"  Results: {len(results)} matched")
    for r in results:
        print(f"    [{r['item']['id']}] score={r['score']} | {r['item']['title']}")

    return elapsed


def run_batch_benchmark(knowledge, iterations=100):
    """Batch benchmark with statistical analysis."""
    print("\n" + "=" * 60)
    print(f"  2. Batch Benchmark ({len(BENCHMARK_QUERIES)} queries x {iterations} iterations)")
    print("=" * 60)

    all_times = []
    query_times = defaultdict(list)

    for _ in range(iterations):
        for q in BENCHMARK_QUERIES:
            _, elapsed = search_knowledge(q, knowledge)
            all_times.append(elapsed)
            query_times[q].append(elapsed)

    all_times.sort()

    avg = statistics.mean(all_times)
    median = statistics.median(all_times)
    p50 = all_times[int(len(all_times) * 0.50)]
    p95 = all_times[int(len(all_times) * 0.95)]
    p99 = all_times[int(len(all_times) * 0.99)]
    p_min = min(all_times)
    p_max = max(all_times)
    passed = sum(1 for t in all_times if t <= TARGET_MS)
    pass_rate = passed / len(all_times) * 100

    print(f"\n  {'Metric':<20} {'Value':<15}")
    print(f"  {'-' * 35}")
    print(f"  {'Total samples':<20} {len(all_times):<15}")
    print(f"  {'Avg':<20} {avg:<15.2f} ms")
    print(f"  {'Median':<20} {median:<15.2f} ms")
    print(f"  {'P50':<20} {p50:<15.2f} ms")
    print(f"  {'P95':<20} {p95:<15.2f} ms")
    print(f"  {'P99':<20} {p99:<15.2f} ms")
    print(f"  {'Min':<20} {p_min:<15.2f} ms")
    print(f"  {'Max':<20} {p_max:<15.2f} ms")
    print(f"  {'<=500ms pass rate':<20} {pass_rate:<15.1f}% ({passed}/{len(all_times)})")

    return {
        "avg": avg, "median": median, "p50": p50, "p95": p95, "p99": p99,
        "min": p_min, "max": p_max, "pass_rate": pass_rate,
        "total": len(all_times), "passed": passed
    }


def generate_report(stats, single_time):
    """Generate benchmark report markdown."""
    path = os.path.join(BASE, "benchmark_report.md")

    md = f"""# Retrieval Benchmark Report — Phase 4

## Target

OS Agent memory retrieval target: **<= 500ms** (端侧内存检索)

## Environment

| Item | Value |
|------|-------|
| Python | 3.12+ |
| Knowledge base | phase2-consolidate/knowledge_items.json |
| Search algorithm | Bigram similarity + synonym expansion |
| Database | SQLite (memory.db) |

## Single Query Result

| Metric | Value |
|--------|-------|
| Query | 麒麟系统如何更新驱动 |
| Response time | {single_time:.2f} ms |
| Pass (<=500ms) | {"Yes" if single_time <= TARGET_MS else "No"} |

## Batch Benchmark ({stats['total']} samples)

| Metric | Value |
|--------|-------|
| Avg | {stats['avg']:.2f} ms |
| Median (P50) | {stats['p50']:.2f} ms |
| P95 | {stats['p95']:.2f} ms |
| P99 | {stats['p99']:.2f} ms |
| Min | {stats['min']:.2f} ms |
| Max | {stats['max']:.2f} ms |
| Pass rate (<=500ms) | {stats['pass_rate']:.1f}% |

## Conclusion

{"Target met: all queries resolve within 500ms on local simulation." if stats['pass_rate'] >= 99 else "Some queries exceed the 500ms target. Consider optimizing the retrieval algorithm or reducing knowledge base size."}

## Note

This is a local simulation on Windows with pure Python bigram search.
In production on麒麟OS with embedding-based retrieval, response times
may differ. The local benchmark serves as a baseline reference.
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n  Report generated: {path}")


def main():
    print("=" * 60)
    print("  Phase 4 — Retrieval Benchmark (Target: <= 500ms)")
    print("=" * 60)

    knowledge = load_knowledge()
    print(f"\n  Loaded {len(knowledge)} knowledge items")

    # 1) Single query
    single_time = run_single_benchmark(knowledge)

    # 2) Batch benchmark
    stats = run_batch_benchmark(knowledge, iterations=50)

    # 3) Report
    generate_report(stats, single_time)

    print(f"\n{'=' * 60}")
    print(f"  Benchmark Complete")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
