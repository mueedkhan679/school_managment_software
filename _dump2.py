import sys  
L=open('config/settings.py',encoding='utf-8').read().splitlines()  
for i in range(165,215): print(f'{i+1}: {L[i]}')  
