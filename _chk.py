import os,sys  
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')  
import django  
django.setup()  
from django.core.management import call_command  
r=call_command('check', interactive=False, verbosity=0)  
print('check_exit=', r)  
