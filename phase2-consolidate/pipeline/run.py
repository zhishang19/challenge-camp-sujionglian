"""
run.py — Phase 2 Pipeline Runner

Executes the 4 pipeline stages in order:
  1. merge_day2.py   (D2: merge & clean raw data)
  2. clean_basic.py   (D3: basic CSV cleaning)
  3. do_git_merge.py  (D3: Git merge demo)
  4. consolidate.py   (Phase 2: full consolidation)

Each stage is run as a subprocess; the runner prints a summary on completion.
"""
import os
import subprocess
import sys
import time


# ═══════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE_DIR)  # phase2-consolidate/
WS_ROOT = os.path.dirname(ROOT)   # workspace root (新建文件夹 (27))

SCRIPTS = [
    {
        "name": "merge_day2.py",
        "path": os.path.join(WS_ROOT, "phase1-basics", "D2", "merge_day2.py"),
        "desc": "D2: Merge & clean raw user_behavior / tool_result",
    },
    {
        "name": "clean_basic.py",
        "path": os.path.join(WS_ROOT, "phase1-basics", "D3", "clean_basic.py"),
        "desc": "D3: Basic CSV cleaning (chat sessions)",
    },
    {
        "name": "do_git_merge.py",
        "path": os.path.join(WS_ROOT, "phase1-basics", "D3", "do_git_merge.py"),
        "desc": "D3: Git merge demo (feature/email → main)",
    },
    {
        "name": "consolidate.py",
        "path": os.path.join(WS_ROOT, "phase2-consolidate", "consolidate.py"),
        "desc": "Phase 2: Full consolidation (7 modules)",
    },
]


def run_script(script_info: dict) -> dict:
    """Run a Python script as a subprocess and return execution result."""
    path = script_info["path"]
    name = script_info["name"]
    desc = script_info["desc"]

    print(f"\n{'=' * 60}")
    print(f"  [{script_info['name']}] {desc}")
    print(f"  File: {path}")
    print(f"{'=' * 60}")

    if not os.path.exists(path):
        print(f"  [SKIP] SKIPPED: File not found at {path}")
        return {"name": name, "status": "skipped", "output": "File not found", "duration": 0}

    start = time.time()
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=os.path.dirname(path),
            timeout=120,
            env=env,
        )
        duration = time.time() - start
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode == 0:
            status = "ok"
            print(f"  [OK] SUCCESS ({duration:.1f}s)")
        else:
            status = "error"
            print(f"  [FAIL] FAILED (exit={result.returncode}, {duration:.1f}s)")

        for line in stdout.splitlines()[-5:]:
            # Replace unicode replacement chars that crash GBK terminal
            print(f"  | {line.replace('\ufffd', '?')}")
        if stderr and status == "error":
            print(f"  | [STDERR] {stderr[:200].replace('\ufffd', '?')}")

        return {"name": name, "status": status, "output": stdout[:500], "duration": duration}

    except subprocess.TimeoutExpired:
        duration = time.time() - start
        print(f"  ❌ TIMEOUT ({duration:.1f}s)")
        return {"name": name, "status": "timeout", "output": "", "duration": duration}
    except Exception as e:
        duration = time.time() - start
        print(f"  [FAIL] EXCEPTION: {e}")
        return {"name": name, "status": "exception", "output": str(e), "duration": duration}


def print_summary(results: list):
    """Print pipeline execution summary."""
    total = len(results)
    ok = sum(1 for r in results if r["status"] == "ok")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] in ("error", "timeout", "exception"))
    total_dur = sum(r["duration"] for r in results)

    print(f"\n{'=' * 60}")
    print(f"  Pipeline Summary")
    print(f"{'=' * 60}")
    print(f"  Total stages:  {total}")
    print(f"  Successful:    {ok}")
    print(f"  Skipped:       {skipped}")
    print(f"  Failed:        {failed}")
    print(f"  Total time:    {total_dur:.1f}s")
    print(f"{'─' * 60}")
    for r in results:
        icon = {"ok": "[OK]", "skipped": "[SKIP]", "error": "[FAIL]", "timeout": "[TIME]", "exception": "[ERR]"}.get(r["status"], "?")
        print(f"  {icon} {r['name']:20s} {r['status']:10s} {r['duration']:.1f}s")
    print(f"{'=' * 60}")

    if failed > 0:
        print(f"\n  [!] {failed} stage(s) failed. Check output above for details.")
        sys.exit(1)
    else:
        print(f"\n  [DONE] Pipeline completed successfully!")
        sys.exit(0)


def main():
    print("=" * 60)
    print("  Phase 2 Pipeline Runner")
    print(f"  Working directory: {WS_ROOT}")
    print("=" * 60)

    results = []
    for script in SCRIPTS:
        result = run_script(script)
        results.append(result)

    print_summary(results)


if __name__ == "__main__":
    main()
