"""
do_git_merge.py - Build Git repo in subdir using hashlib+zlib.
Safe: git repo is in git_demo/ subdir, won't touch workspace files.
"""
import os, hashlib, zlib, time, subprocess, re, locale

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(BASE, "git_demo")

def run_git(args):
    """Run git command with robust encoding handling for Chinese Windows."""
    try:
        r = subprocess.run(args, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except Exception:
        r = subprocess.run(args, capture_output=True)
        sys_enc = locale.getpreferredencoding()
        r.stdout = r.stdout.decode(sys_enc, errors="replace") if r.stdout else ""
        r.stderr = r.stderr.decode(sys_enc, errors="replace") if r.stderr else ""
    return r
CB_SRC = os.path.join(BASE, "clean_basic.py")  # source file outside repo

# Remove old git_demo
import shutil
if os.path.exists(REPO):
    shutil.rmtree(REPO, ignore_errors=True)

os.makedirs(REPO, exist_ok=True)

# Initialize git repo properly
run_git(["git", "-C", REPO, "init"])
run_git(["git", "-C", REPO, "config", "user.name", "Student"])
run_git(["git", "-C", REPO, "config", "user.email", "student@example.com"])

GIT_DIR = os.path.join(REPO, ".git")

def write_object(data, obj_type):
    if isinstance(data, str):
        data = data.encode()
    header = f"{obj_type} {len(data)}\0".encode()
    store = header + data
    sha1 = hashlib.sha1(store).hexdigest()
    compressed = zlib.compress(store)
    obj_dir = os.path.join(GIT_DIR, "objects", sha1[:2])
    os.makedirs(obj_dir, exist_ok=True)
    with open(os.path.join(obj_dir, sha1[2:]), "wb") as f:
        f.write(compressed)
    return sha1

def write_blob(filepath):
    with open(filepath, "rb") as f:
        return write_object(f.read(), "blob")

def write_tree(entries):
    data = b""
    for mode, name, sha1 in sorted(entries, key=lambda x: x[1]):
        data += f"{mode} {name}".encode() + b"\0"
        data += bytes.fromhex(sha1)
    return write_object(data, "tree")

def write_commit(tree_sha, parent_shas, message, author_time=None):
    if author_time is None:
        author_time = int(time.time())
    data = f"tree {tree_sha}\n"
    for p in parent_shas:
        data += f"parent {p}\n"
    data += f"author Student <student@example.com> {author_time} +0800\n"
    data += f"committer Student <student@example.com> {author_time} +0800\n"
    data += f"\n{message}\n"
    return write_object(data.encode(), "commit")

# Copy source files into repo (so checkout doesn't delete them)
for f in ["merge_day2.py", "merged.jsonl", "clean_basic.py", "chat_sessions_clean.csv", "review_log.txt"]:
    src = os.path.join(BASE, "..", "D2", f) if f.endswith(".py") or f.endswith(".jsonl") else os.path.join(BASE, f)
    if not os.path.exists(src):
        src = os.path.join(BASE, f)
    if os.path.exists(src):
        dst = os.path.join(REPO, f)
        import shutil; shutil.copy2(src, dst)

blobs = {}
print("Creating blobs...")
for f in ["merge_day2.py", "merged.jsonl", "clean_basic.py", "chat_sessions_clean.csv", "review_log.txt"]:
    fp = os.path.join(REPO, f)
    if os.path.exists(fp):
        blobs[f] = write_blob(fp)
        print(f"  {f}: {blobs[f][:8]}")

d3_entries = [(f[1], f[0], blobs[f[0]]) for f in [("review_log.txt", "100644"), ("chat_sessions_clean.csv", "100644"), ("clean_basic.py", "100644")]]
d3_tree = write_tree(d3_entries)

d2_entries = [(f[1], f[0], blobs[f[0]]) for f in [("merged.jsonl", "100644"), ("merge_day2.py", "100644")]]
d2_tree = write_tree(d2_entries)

root_entries = [("040000", d, t) for d, t in [("d2", d2_tree), ("d3", d3_tree)]]
root_tree = write_tree(root_entries)

t0 = 1000000000
c1 = write_commit(root_tree, [], "init: base files", t0)
with open(os.path.join(GIT_DIR, "refs", "heads", "main"), "w") as f: f.write(c1 + "\n")

# Feature branch changes clean_basic.py
with open(CB_SRC, "r", encoding="utf-8") as f:
    original = f.read()
pos = original.find("def normalize_time(") if "def normalize_time(" in original else len(original) // 2

fb_content = original[:pos] + (
    '\n'
    'def mask_email(text):\n'
    '    masked = False\n'
    '    new_text = re.sub(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+)", r"***@\\2", text)\n'
    '    if new_text != text: masked = True\n'
    '    return new_text, masked\n\n'
) + original[pos:]

fb_sha = write_object(fb_content.encode(), "blob")
fb_entries = [("100644", "clean_basic.py", fb_sha)]
for mode, name, sha in d3_entries:
    if name != "clean_basic.py":
        fb_entries.append((mode, name, sha))
fb_d3_tree = write_tree(fb_entries)
fb_root = write_tree([("040000", "d2", d2_tree), ("040000", "d3", fb_d3_tree)])
c2 = write_commit(fb_root, [c1], "feat: add email masking", t0 + 1000)
os.makedirs(os.path.join(GIT_DIR, "refs", "heads", "feature"), exist_ok=True)
with open(os.path.join(GIT_DIR, "refs", "heads", "feature", "email"), "w") as f: f.write(c2 + "\n")

# Main branch different version
mb_content = original[:pos] + (
    '\n'
    'def mask_email(text):\n'
    '    found = bool(re.search(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+)", text))\n'
    '    return text, found\n\n'
) + original[pos:]

mb_sha = write_object(mb_content.encode(), "blob")
mb_entries = [("100644", "clean_basic.py", mb_sha)]
for mode, name, sha in d3_entries:
    if name != "clean_basic.py":
        mb_entries.append((mode, name, sha))
mb_d3_tree = write_tree(mb_entries)
mb_root = write_tree([("040000", "d2", d2_tree), ("040000", "d3", mb_d3_tree)])
c3 = write_commit(mb_root, [c1], "feat: conservative email detection", t0 + 2000)
with open(os.path.join(GIT_DIR, "refs", "heads", "main"), "w") as f: f.write(c3 + "\n")

# Git CLI verify
print("\n=== git checkout main ===")
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
r = run_git(["git", "-C", REPO, "checkout", "main", "-f"])
print(r.stdout.strip() if r.stdout.strip() else "(checkout main)")
if r.stderr.strip():
    print(f"stderr: {r.stderr.strip()[:200]}")

print("\n=== git log --all ===")
r = run_git(["git", "-C", REPO, "log", "--oneline", "--graph", "--all"])
print(r.stdout.strip() if r.stdout.strip() else "(empty)")

print("\n=== git merge ===")
r = run_git(["git", "-C", REPO, "merge", "feature/email", "--no-edit"])
output = (r.stdout + r.stderr).strip()
if r.returncode == 0:
    print(f"Merge OK! {output[:200]}")
else:
    print(f"Merge failed (rc={r.returncode}): {output[:500]}")
    # Check working tree for conflict
    cb_path = os.path.join(REPO, "clean_basic.py")
    if os.path.exists(cb_path):
        with open(cb_path, "r", encoding="utf-8") as f:
            content = f.read()
            if "<<<<<<<" in content:
                print("  Conflict markers found in clean_basic.py — needs manual resolution")

print("\nDONE")
