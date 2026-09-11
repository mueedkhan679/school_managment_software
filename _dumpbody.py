from pathlib import Path  
p=Path('apps/tenants/utils.py')  
lines=p.read_text(encoding='utf-8').splitlines()  
n=len(lines)  
for i in range(26, n): print(f'{i+1:04d}: {lines[i]}')  
