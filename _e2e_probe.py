import os, sys, time, sqlite3, unicodedata, re
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.tenants.models import Tenant
from apps.tenants.utils import ensure_tenant_admin, migrate_tenant_db, register_tenant_db
from django.db import connections

slug = 'e2e-' + re.sub(r'\W+', '', unicodedata.normalize('NFKD', str(time.time())))[:10]
print('PROVISIONING TENANT SLUG:', slug)

t = Tenant(
    name='E2E Test School',
    slug=slug,
    status='ACTIVE',
)
t.save()

print('tenant.id =', t.id)
print('tenant.db_alias =', t.db_alias)
print('migrate_tenant_db returns:', migrate_tenant_db(t, interactive=False, verbosity=0))
print('register_tenant_db returns:', register_tenant_db(t))
print('ensure_tenant_admin returns:', ensure_tenant_admin(t))

# Locate the tenant DB file via Django's router alias -> database setting.
db_alias = t.db_alias
db_info = connections[db_alias]
db_path = getattr(db_info, 'database', None)
if not db_path or not db_path.startswith('sqlite:'):
    print('could not resolve tenant DB path from alias', db_alias)
    print('settings DATABASES entries:', {k: v.get('ENGINE') for k, v in __import__('config.settings', fromlist=['DATABASES']).DATABASES.items()})
    raise SystemExit(1)
path_only = db_path.split(':', 1)[1]
print('\ntenant DB alias =', db_alias)
print('tenant DB file =', os.path.abspath(path_only))
print('file exists =', os.path.exists(path_only))

conn = sqlite3.connect(path_only)
try:
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    print('\n=== TABLES IN TENANT DB ===')
    for tbl in tables:
        print('   ', tbl)
    auth = conn.execute("SELECT id,username,role,is_staff,is_superuser,is_active,is_superadmin FROM auth_user LIMIT 20").fetchall()
    print('\n=== auth_user rows ===')
    for row in auth:
        print('   ', row)
    admin = conn.execute("SELECT id,username,role,is_staff,is_superuser,is_active,is_superadmin FROM auth_user WHERE username='admin'").fetchone()
    print('\n=== admin user (username=admin) ===')
    print('   ', admin)
finally:
    conn.close()

