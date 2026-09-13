import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.contrib.auth import get_user_model
from apps.tenants.signals import ensure_tenant_admin

User = get_user_model()
print('User model:', User.__name__)
print('ensure_tenant_admin callable:', callable(ensure_tenant_admin))

# Confirm the admin creation function references the right permission flags.
import inspect
src = inspect.getsource(ensure_tenant_admin)
for kw in ['is_superuser', 'is_staff', 'is_active', 'is_superadmin', 'role = Role.ADMIN', 'adminpassword123']:
    print(f'contains {kw!r}:', kw in src)

print('OK')
