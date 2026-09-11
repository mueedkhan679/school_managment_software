from pathlib import Path  
p=Path('apps/tenants/utils.py')  
lines=p.read_text(encoding='utf-8').splitlines()  
for i,ln in enumerate(lines,1):  
  s=ln.strip()  
  if any(k in s for k in ['def ','class ','MigrationLoader','def migrate_tenant_db','def ensure_tenant_migrations','def _repair_missing_tables','def _resolve_repair_changes','def _creating_migration_map','def _list_tenant_tables','TENANT_AUTO_REPAIR','ensure_tenant_migrations(']):  
    print(f'{i:04d}: {ln.rstrip()}')  
