import os,sys  
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')  
import django  
django.setup()  
from apps.tenants.utils import ADMIN_USERNAME, ADMIN_PASSWORD, set_default_admin_user_credentials  
print('ADMIN_USERNAME=',repr(ADMIN_USERNAME),'ADMIN_PASSWORD=',repr(ADMIN_PASSWORD))  
from django.conf import settings  
print('settings.MASTER_ADMIN_USERNAME=',repr(getattr(settings,'MASTER_ADMIN_USERNAME','__MISSING__')))  
print('settings.MASTER_ADMIN_PASSWORD=',repr(getattr(settings,'MASTER_ADMIN_PASSWORD','__MISSING__')))  
from django.apps import apps; from apps.accounts.models import Role, User  
from unittest.mock import MagicMock  
u=MagicMock(); set_default_admin_user_credentials(u, Role)  
print('flags set -=',u.is_superuser,'is_staff=',u.is_staff,'is_active=',u.is_active,'role=',u.role,'is_superadmin=',u.is_superadmin)  
