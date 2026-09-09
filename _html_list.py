"""Enumerate HTML templates under the project."""
from pathlib import Path

root = Path(__file__).resolve().parent

for p in sorted(root.rglob("*.html")):
    print(p)

print("---- tenant templates dir ----")
tdir = root / "templates" / "tenants"
if tdir.is_dir():
    for p in sorted(tdir.iterdir()):
        print(p)
else:
    print("templates/tenants dir does NOT exist")
