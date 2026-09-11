import sys  
L=open('apps/tenants/utils.py',encoding='utf-8').read().splitlines()  
for i in range(440,560): print(f'{i+1}: {L[i]}')  
