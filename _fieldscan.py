import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from apps.tenants.models import Tenant
for f in Tenant._meta.get_fields():
    print(f.name, '|', f.get_internal_type() if hasattr(f, 'get_internal_type') else type(f).__name__, '|', getattr(f, 'max_length', None))
