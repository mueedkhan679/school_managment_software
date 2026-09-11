import pathlib, sys

site = pathlib.Path(r'C:\Users\ytmoi\AppData\Local\Programs\Python\Python314\Lib\site-packages')
print('site-packages exists:', site.exists())

print()
print('=== django-notifier-backend files in site-packages ===')
count = 0
for p in site.rglob('*.py'):
    if 'notifier' in str(p).lower():
        print(p)
        count += 1
print('total notifier py files:', count)

print()
print('=== django template/base.py (get_nodes_by_type source) ===')
for p in site.rglob('template/base.py'):
    print(p)
    break

print()
print('=== this project root ===')
proj = pathlib.Path('.')
print('cwd:', proj.resolve())
print('children (non-_):')
for p in sorted(proj.iterdir()):
    if p.name.startswith('_'):
        continue
    if p.is_dir():
        print(' DIR:', p.name)
    else:
        print(' FILE:', p.name)
