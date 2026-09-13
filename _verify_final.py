import os, sys, subprocess

PY = r'C:\Users\ytmoi\AppData\Local\Programs\Python\Python314\python.exe'
ROOT = r'c:\Users\ytmoi\Desktop\school_project'

def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r

print('=== manage.py check ===')
r = run([PY, 'manage.py', 'check'])
print('exit_code:', r.returncode)
out = (r.stdout or '') + (r.stderr or '')
for line in out.splitlines():
    if line.strip():
        print('  ', line.strip())

print('\n=== import + attribute sanity (apps/tenants/utils) ===')
r2 = run([PY, '-c', 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings"); import django; django.setup(); from apps.tenants import utils; print("utils OK; has ensure_tenant_admin:", hasattr(utils,"ensure_tenant_admin")); print("has ensure_tenant_migrations:", hasattr(utils,"ensure_tenant_migrations"))'])
print('exit:', r2.returncode)
print('stdout:', (r2.stdout or '').strip())
print('stderr:', (r2.stderr or '').strip())
