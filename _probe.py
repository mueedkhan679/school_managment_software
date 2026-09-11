import sys  
L = open('config/settings.py', encoding='utf-8').read().splitlines()  
print('TOTAL LINES:', len(L))  
print()  
patterns = ['BaseHookConfig', 'ct_config', 'is_response_delayed', 'load_template', 'build_standby_response', 'INNER_STATUS', 'DoWaitNode', 'original_template', 'do_wait']  
for pat in patterns:  
    print('--- matches for', repr(pat), '---')  
    for i, line in enumerate(L, 1):  
        if pat in line:  
            print(i, ':', line)  
    print()  
print('=== DONE ===')  
 
