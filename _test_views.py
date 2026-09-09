"""Test the master admin views using Django test Client (full middleware stack).

Uses a unique slug each run to avoid conflicts. Cleans up after itself.
"""
import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.db import connections
from apps.tenants.models import Tenant
from apps.tenants.utils import register_tenant_db, delete_tenant_db
from pathlib import Path

User = get_user_model()

RUN_ID = Path(".test_run_id").read_text().strip() if Path(".test_run_id").exists() else "manual"
TEST_SLUG = f"test-{RUN_ID}"

client = Client()
su = User.objects.filter(is_superadmin=True).first()
if not su:
    print("[ERROR] No superadmin user found")
    sys.exit(1)
client.force_login(su)

print("=" * 60)
print(f"TEST: Master Admin Views (run_id={RUN_ID})")
print("=" * 60)

results = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    line = f"  [{status}] {name}"
    if detail:
        line += f" -- {detail}"
    print(line)
    return condition

# 1. master_dashboard GET
resp = client.get("/master-admin/")
ok = check("master_dashboard GET", resp.status_code == 200,
           f"status={resp.status_code}")
results.append(("master_dashboard GET", ok))

# 2. school_add GET
resp = client.get("/master-admin/add/")
ok = check("school_add GET", resp.status_code == 200,
           f"status={resp.status_code}")
results.append(("school_add GET", ok))

# 3. school_add POST
resp = client.post("/master-admin/add/", {
    "school_name": f"Test School {RUN_ID}",
    "slug": TEST_SLUG,
    "admin_email": f"admin@{TEST_SLUG}.local",
    "admin_phone": "0300-1234567",
    "max_students": "200",
}, follow=False)
new_t = Tenant.objects.filter(slug=TEST_SLUG).first()
ok = check("school_add POST", resp.status_code == 302 and new_t is not None,
           f"status={resp.status_code}" +
           (f", redirect={resp.url}" if resp.status_code == 302 else ""))
if ok:
    register_tenant_db(new_t)
    ok2 = check("  tenant DB registered",
                new_t.db_alias in connections.databases,
                f"alias={new_t.db_alias}")
    results.append(("school_add POST - DB registered", ok2))
else:
    print(f"      response body: {resp.content.decode('utf-8')[:500]}")
results.append(("school_add POST", ok))

# 4. school_edit GET
resp = client.get(f"/master-admin/{new_t.slug}/edit/")
ok = check("school_edit GET", resp.status_code == 200,
           f"status={resp.status_code}")
results.append(("school_edit GET", ok))

# 5. school_edit POST
resp = client.post(f"/master-admin/{new_t.slug}/edit/", {
    "school_name": f"Test School {RUN_ID} (Updated)",
    "admin_email": f"updated@{TEST_SLUG}.local",
    "admin_phone": "0300-9999999",
    "max_students": "1000",
}, follow=False)
ok = check("school_edit POST", resp.status_code == 302,
           f"status={resp.status_code}")

# 6. school_toggle POST -- suspend
resp = client.post(f"/master-admin/{new_t.slug}/toggle/", {}, follow=False)
ok = check("school_toggle POST (suspend)", resp.status_code == 302,
           f"status={resp.status_code}")
if ok:
    new_t.refresh_from_db()
    ok2 = check("  tenant suspended", not new_t.is_active,
                f"is_active={new_t.is_active}")
    results.append(("school_toggle - suspended", ok2))
results.append(("school_toggle POST", ok))

# 7. Kill Switch: suspended tenant -> 403
resp = client.get(f"/t/{new_t.slug}/anything/")
ok = check("Kill Switch 403 (suspended)",
           resp.status_code == 403
           and b"Account Suspended" in resp.content,
           f"status={resp.status_code}, "
           f"has_text={b'Account Suspended' in resp.content}")
results.append(("Kill Switch 403", ok))

# Resume tenant
new_t.is_active = True
new_t.save()
resp = client.get(f"/t/{new_t.slug}/anything/")
ok = check("Active tenant NOT 403",
           resp.status_code != 403,
           f"status={resp.status_code} (kill switch off)")
results.append(("Active tenant not 403", ok))

# 8. school_reset_password GET
resp = client.get(f"/master-admin/{new_t.slug}/reset-password/")
ok = check("school_reset_password GET", resp.status_code == 200,
           f"status={resp.status_code}")
if ok:
    content = resp.content.decode("utf-8")
    ok2 = check("  form has 'Reset Password'",
                "Reset Password" in content, "")
    ok3 = check("  form has 'New Password'",
                "New Password" in content, "")
    results.append(("school_reset_password - form fields",
                    ok2 and ok3))
results.append(("school_reset_password GET", ok))

# 9. school_reset_password POST
from apps.accounts.models import Role
User2 = get_user_model()
admin_users = User2.objects.using(new_t.db_alias).filter(
    role=Role.ADMIN)
target = admin_users.first()
if target:
    resp = client.post(
        f"/master-admin/{new_t.slug}/reset-password/", {
            "user_id": str(target.id),
            "new_password": "newpass123",
        }, follow=False)
    ok = check("school_reset_password POST",
               resp.status_code == 302, f"status={resp.status_code}")
    if ok:
        target.refresh_from_db(using=new_t.db_alias)
        from django.contrib.auth.hashers import check_password
        ok2 = check("  password actually changed",
                    check_password("newpass123", target.password),
                    "check_password verified")
        results.append(
            ("school_reset_password - password changed", ok2))
    results.append(("school_reset_password POST", ok))
else:
    print("  [SKIP] No admin user in tenant DB")
    results.append(("school_reset_password POST", None))

# 10. Cleanup
print()
print("  --- Cleanup ---")
try:
    delete_tenant_db(new_t)
    new_t.delete()
    print(f"  [OK] Deleted test tenant "
          f"'{new_t.school_name}' and its DB")
except Exception as e:
    print(f"  [WARN] Cleanup failed: {e}")

# Summary
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
all_passed = True
for name, passed in results:
    if passed is None:
        status = "SKIP"
    else:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
    print(f"  [{status}] {name}")

print(f"\nOverall: "
      f"{'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
sys.exit(0 if all_passed else 1)

if ok:
    new_t.refresh_from_db()
    ok2 = check("  fields updated",
                new_t.school_name == f"Test School {RUN_ID} (Updated)"
                and new_t.admin_email == f"updated@{TEST_SLUG}.local",
                f"name={new_t.school_name}, email={new_t.admin_email}")
    results.append(("school_edit POST - fields", ok2))
results.append(("school_edit POST", ok))