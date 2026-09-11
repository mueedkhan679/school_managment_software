import sys  
L=open('config/settings.py',encoding='utf-8').read().splitlines()  
print('TOTAL LINES:', len(L))  
print('=== ct_config region ===')  
m=next((i for i,l in enumerate(L) if 'class ct_config' in l), None)  
if m is not None: print(f'ct_config at line {m+1}'); [print(f'{j+1}: {L[j]}') for j in range(m, min(m+90, len(L))) if 'BaseHookConfig' in L[j] or 'load_template' in L[j] or 'is_default_affecting' in L[j] or 'IS_DEFAULT' in L[j]]  
