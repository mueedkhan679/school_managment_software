import os,sys  
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')  
sys.path.insert(0,'.')  
import django  
django.setup()  
from apps.tenants.db_router import set_current_db_alias  
import inspect  
print('set_current_db_alias sig:', inspect.signature(set_current_db_alias))  
from apps.tenants.utils import provision_tenant_db  
print('provision_tenant_db sig:', inspect.signature(provision_tenant_db))  
print('Source lines of migrate_tenant_db:', [ln for ln in inspect.getsource(provision_tenant_db).splitlines() if 'migrate' in ln.lower() or 'def ' in ln or 'call_command' in ln][:8])  
