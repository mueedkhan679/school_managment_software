import sys, re
from pathlib import Path

with open("apps/tenants/utils.py", encoding="utf-8") as f:
    t = f.read()
print("TOTAL LINES", len(t.splitlines()))

for fn in ["ensure_tenant_admin", "migrate_tenant_db", "provision_tenant_db", "ensure_tenant_migrations", "register_tenant_db"]:
    m = re.search(
        r"^(def " + fn + r"\([^\n]*\)\n)((?:    [^\n]*\n)+?)(?=\n(?:def |class |__|) |\Z)",
        t, re.S,
    )
    print("==== %s ====" % fn)
    print(m.group(0) if m else "NOT FOUND")
    print()
