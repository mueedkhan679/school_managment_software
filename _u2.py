import sys  
L=open('apps/tenants/utils.py',encoding='utf-8').read().splitlines()  
start=None  
for i,ln in enumerate(L,1):  
  if ln.strip().startswith('def provision_tenant_db') and start is None: start=i  
  if start: print(f'{i}: {ln}')  
  if start and ln.strip().startswith('def ') and i print('---END---'); break  
print('TOTAL LINES:', len(L))  
