import os, sys, re

# 1) Confirm the signal receiver is actually connected.
probe_log = '_final_probe_chk.txt'
if not os.path.exists(probe_log):
    print('no probe log at', probe_log)
    raise SystemExit(1)
src = open(probe_log, encoding='utf-8', errors='replace').read()
print('=== SIGNAL RECEIVER CONNECTED (from probe log) ===')
for line in src.splitlines():
    if 'SIGNAL RECEIVER CONNECTED' in line or 'migrate_tenants_post_migrate' in line:
        print(line.strip())

# 2) Confirm the top-level imports and constants are sane.
utils_path = 'apps/tenants/utils.py'
txt = open(utils_path, encoding='utf-8').read()
lines = txt.splitlines()

def find_line(needle):
    for i, l in enumerate(lines, 1):
        if needle in l:
            return i
    return None

print('\n=== KEY LINES IN utils.py ===')
for needle in [
    'context_processors',
    'ApiConfig',
]:
    ln = find_line(needle)
    print(f'  {needle!r} at line {ln}' if ln else f'  {needle!r} NOT FOUND')

# settings.py context-processor wire
stxt = open('config/settings.py', encoding='utf-8').read()
print('\n=== context_processors wire in settings.py ===')
for m in re.finditer(r'context_processors\)\s*[,\)]\s*[,\s]*api\.apps\.ApiConfig\.tenant_context', stxt):
    print('  OK: api.apps.ApiConfig.tenant_context wired')
print('  (no match printed above means it may already be wired differently)')
PYEOF