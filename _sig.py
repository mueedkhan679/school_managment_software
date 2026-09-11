import os,sys  
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')  
sys.path.insert(0,'.')  
import django  
django.setup()  
from apps.tenants.db_router import set_current_db_alias, DatabaseRouter  
import inspect  
print('set_current_db_alias sig:', inspect.signature(set_current_db_alias))  
print('router DB_FOR_WRITE:', getattr(DatabaseRouter,'DB_FOR_WRITE',None))  
from apps.tenants.utils import provision_tenant_db  
print('provision_tenant_db sig:', inspect.signature(provision_tenant_db))  
print('provision_tenant_db funcs:', [a for a in dir(provision_tenant_db) if not a.startswith('_')])  
