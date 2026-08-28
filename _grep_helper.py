"""Temp helper: grep patterns in text files. Usage: py _grep_helper.py pattern file1 file2 ..."""
import sys

pattern = sys.argv[1]
for path in sys.argv[2:]:
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError as exc:
        print(f"!! cannot read {path}: {exc}")
        continue
    hits = 0
    for i, line in enumerate(lines, 1):
        if pattern.lower() in line.lower():
            print(f"{path}:{i}: {line.strip()}")
            hits += 1
    if not hits:
        print(f"{path}: (no match for {pattern!r})")
