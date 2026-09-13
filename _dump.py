import sys  
L=open('apps/tenants/utils.py',encoding='utf-8').read().splitlines()  
print('TOTAL', len(L))  
import re  
t='\n'.join(L)  
for fn in ['ensure_tenant_admin','migrate_tenant_db','provision_tenant_db','ensure_tenant_migrations','register_tenant_db']:  
