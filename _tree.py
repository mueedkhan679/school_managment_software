import sys  
from pathlib import Path  
p=Path('apps')  
print('apps files:'); [print(' ', f) for f in p.rglob('*.py')]  
