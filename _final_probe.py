import os
from pathlib import Path

root = Path('.')
out = root / '_final_probe.log'
out.write_text('START probe\n', encoding='utf-8')

def grep(path, needle_lines, label):
    out.write(f'\n===== {label} =====\n')
    try:
        text = Path(path).read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        out.write(f'ERR reading {path}: {e}\n')
        return
    lines = text.splitlines()
    text_joined = '\n'.join(lines)
    for needle in needle_lines:
        out.write(f'--- occurrences of: {needle!r} ---\n')
        hits = 0
        for i, ln in enumerate(lines, 1):
            if needle in ln:
                out.write(f'{i:04d}: {ln.rstrip()}\n')
                hits += 1
        if hits == 0:
            out.write('  (none)\n')
        else:
            out.write(f'  ({hits} hit(s))\n')

# 1. settings: password default + auth backends + db routers + DATABASES master
grep('config/settings.py',
     ['MASTER_DEFAULT_ADMIN_PASSWORD',
      'AUTHENTICATION_BACKENDS',
      'DATABASE_ROUTERS',
      'DATABASES = {',
      'TENANT_AUTO_REPAIR',
      'MIDDLEWARE',
      'AUTH_USER_MODEL'],
     'config/settings.py')

# 2. tenant model: db_alias / db_file helpers + adding logic + db_router alias
grep('apps/tenants/models.py',
     ['class Tenant',
      'def db_file',
      'def db_alias',
      'db_alias',
      'db_file',
      'tenant_',
      '_state.adding',
      'MigrationRecorder',
      'call_command'],
     'apps/tenants/models.py')

# 3. signals
grep('apps/tenants/signals.py',
     ['pre_save', 'post_save', 'Tenant', 'migrate_tenant_db', 'ensure_tenant_admin', 'provision_tenant_db'],
     'apps/tenants/signals.py')

# 4. apps.py ready
grep('apps/tenants/apps.py',
     ['pre_save', 'post_save', 'Tenant', 'ready', 'signals', 'import'],
     'apps/tenants/apps.py')

# 5. utils: ensure_tenant_admin + provision_tenant_db + defaults + add linear system
grep('apps/tenants/utils.py',
     ['def ensure_tenant_admin',
      'admin_username',
      'admin_password',
      'MASTER_DEFAULT_ADMIN_PASSWORD',
      'provision_tenant_db',
      'migrate_tenant_db',
      'def migrate_tenant_db',
      'ensure_tenant_admin(',
      'def ensure_tenant_consistency',
      'set_current_db_alias',
      'MigrationRecorder',
      'create_superuser',
      'add_linear_system_indexes',
      'TENANT_AUTO_REPAIR',
      'call_command'],
     'apps/tenants/utils.py — key functions')
