import re  
print('=== TEMPLATES ===', file=open('_tmpl.txt','w'))  
t=open('config/settings.py',encoding='utf-8').read()  
open('_tmpl.txt','a').write(re.search(r'TEMPLATES *= *\{[]*?\}', t, re.S).group(0))  
open('_tmpl.txt','a').write('\n=== BACKENDS ===\n')  
open('_tmpl.txt','a').write(re.search(r'AUTHENTICATION_BACKENDS *= *\[[\]]*\]', t, re.S).group(0))  
open('_tmpl.txt','a').write('\n=== CONTEXT ===\n')  
open('_tmpl.txt','a').write(re.search(r'context_processors *= *\[[\]]*\]', t, re.S).group(0))  
