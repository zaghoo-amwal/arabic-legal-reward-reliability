"""Check distributable files; report filenames/reasons, never matched secrets.

Generated outputs are ignored for local use but rejected if Git tracks them.
Use --strict for a pristine export (no generated outputs allowed).
"""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
GENERATED = {"runs", "results", "__pycache__", ".venv", "venv"}
FORBIDDEN = {".local_archive", ".codex", ".agents", "node_modules"}
PATTERNS = {
    "local user path": re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/|/(?:private/)?var/folders/|[A-Z]:\\Users\\"),
    "provider token": re.compile(r"sk-(?:ant-api\d*-|proj-)[A-Za-z0-9_-]{16,}|\bgh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "bearer credential": re.compile(r"Bearer\s+[A-Za-z0-9_.-]{24,}"),
    "session metadata": re.compile(r'"(?:session_id|thread_id|clientThreadId)"\s*:\s*"[A-Za-z0-9_-]{16,}"'),
}


def inspect_file(path):
    relative = path.relative_to(ROOT)
    if path.is_symlink():
        return ["symlink"]
    if set(relative.parts) & FORBIDDEN:
        return ["private directory"]
    if path.name.startswith(".env") or path.suffix in {".pem", ".key", ".log", ".jsonl"}:
        return ["private file type"]
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeError, OSError):
        return ["unreviewed binary or unreadable file"]
    return [label for label, pattern in PATTERNS.items() if pattern.search(text)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    files = []
    errors = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if ".git" in rel.parts:
            continue
        if path.is_symlink():
            errors.append((str(rel), "symlink"))
            continue
        if not path.is_file():
            continue
        if set(rel.parts) & GENERATED or path.suffix == ".pyc":
            if args.strict:
                errors.append((str(rel), "generated artifact in pristine export"))
            continue
        files.append(path)
        errors.extend((str(rel), reason) for reason in inspect_file(path))
    if (ROOT / ".git").exists():
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, text=True,
                                 capture_output=True, check=True).stdout.split("\0")
        for name in filter(None, tracked):
            if set(Path(name).parts) & (GENERATED | FORBIDDEN):
                errors.append((name, "private/generated artifact tracked by Git"))
    for name, reason in errors:
        print(f"FAIL {name}: {reason}")
    if errors:
        raise SystemExit(1)
    print(f"PASS: checked {len(files)} distributable files; no configured pattern matched.")


if __name__ == "__main__":
    main()
