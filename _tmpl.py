import sys,re  
t=open('config/settings.py',encoding='utf-8').read()  
m=re.search(r\"TEMPLATES = \[.*?\n\]\", t, re.S)  
print(m.group(0) if m else 'NOT FOUND')  
