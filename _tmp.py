import re  
t=open('config/settings.py',encoding='utf-8').read()  
m=re.search(r'TEMPLATES *= *\{[}]*\}', t, re.S)  
if m: print('=== TEMPLATES ==='); print(m.group(0))  
print('=== BACKENDS ===')  
mb=re.search(r'AUTHENTICATION_BACKENDS *= *\[[\]]*\]', t, re.S)  
if mb: print(mb.group(0))  
