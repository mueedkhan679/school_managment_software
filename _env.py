import os  
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')  
import django  
django.setup()  
from django.db import connections  
from django.apps import apps  
from apps.tenants.utils import (register_tenant_db, get_tenant_db_path, ADMIN_USERNAME, MASTER_DEFAULT_ADMIN_PASSWORD)  
print('ADMIN_USERNAME=', repr(ADMIN_USERNAME))  
print('MASTER_DEFAULT_ADMIN_PASSWORD=', repr(MASTER_DEFAULT_ADMIN_PASSWORD))  
print('settings.MASTER_DEFAULT_ADMIN_PASSWORD=', repr(getattr(django.conf.settings,'MASTER_DEFAULT_ADMIN_PASSWORD','__MISSING__')))  
r=getattr(django.conf.settings,'REST_FRAMEWORK',None); print('RF_AUTH_BKPS=', r.get('DEFAULT_AUTHENTICATION_BACKENDS') if r else None)  
