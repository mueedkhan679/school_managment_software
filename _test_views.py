"""Test the master admin views using Django test Client (full middleware stack).

Uses a unique slug each run to avoid conflicts. Cleans up after itself.
"""
import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
import re

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


# Re-activate the tenant (it was suspended during the kill-switch test)
# so the login flow can proceed.
Tenant.objects.filter(slug=new_t.slug).update(is_active=True)
new_t.refresh_from_db()

# 11. Tenant login flow — verify form action and post-login redirect stay
#     inside the tenant URL space (no more "No school registered with
#     identifier 'accounts'" middleware error).
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("=" * 60)
print(f"TEST: Tenant Login Flow (run_id={RUN_ID})")
print("=" * 60)

register_tenant_db(new_t)
tenant_client = Client()
admin_user = User.objects.using(new_t.db_alias).filter(
    username=f"admin_{new_t.slug.replace('-', '_')}").first()


if admin_user:
    # --- Check login page form (without authentication) ---
    anon_client = Client()
    login_url = f"/t/{new_t.slug}/accounts/login/"
    resp = anon_client.get(login_url)
    ok_t = check("tenant login page GET",
                 resp.status_code == 200,
                 f"status={resp.status_code}")
    results.append(("tenant login page GET", ok_t))

    # Verify the form action is the tenant-scoped path (not /accounts/login/).
    content = resp.content.decode("utf-8")
    ok_t2 = check("  form action is request.path (tenant-scoped)",
                  f'action="{login_url}"' in content
                  or 'action="/t/' in content,
                  f"found tenant-scoped action in form")
    results.append(("  form action tenant-scoped", ok_t2))

    # Verify the form does NOT contain the hardcoded global URL.
    ok_t3 = check("  form action NOT /accounts/login/",
                  'action="/accounts/login/"' not in content,
                  "no hardcoded global login URL in form")
    results.append(("  form action not global", ok_t3))

    # --- Test full POST login flow inside the tenant context ---
    tenant_client.logout()
    resp = tenant_client.post(login_url, {
        "username": admin_user.username,
        "password": "newpass123",
    }, follow=False)
    ok_t4 = check("tenant login POST succeeds",
                  resp.status_code == 302,
                  f"status={resp.status_code}")
    results.append(("tenant login POST", ok_t4))

    if ok_t4:
        redirect_url = resp.url or ""
        ok_t5 = check("  redirect is tenant-scoped (not /dashboard/)",
                      redirect_url.startswith(f"/t/{new_t.slug}/"),
                      f"redirect={redirect_url}")
        results.append(("  redirect tenant-scoped", ok_t5))

        resp2 = tenant_client.get(redirect_url, follow=False)
        ok_t6 = check("  follow redirect -- valid tenant page",
                      resp2.status_code == 200,
                      f"status={resp2.status_code}")
        results.append(("  follow redirect OK", ok_t6))
else:
    print("  [SKIP] No admin user in tenant DB")
    results.append(("tenant login page GET", None))
    results.append(("  form action tenant-scoped", None))
    results.append(("  form action not global", None))
    results.append(("tenant login POST", None))
    results.append(("  redirect tenant-scoped", None))
    results.append(("  follow redirect OK", None))


    # --- Test full POST login flow inside the tenant context ---

# Cleanup
try:
    delete_tenant_db(new_t)
    new_t.delete()
    print(f"  [OK] Cleaned up test tenant '{new_t.school_name}'")
except Exception as e:
    print(f"  [WARN] Cleanup failed: {e}")

# ---------------------------------------------------------------------------
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
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
all_passed = True
for name, ok in results:
    if ok is None:
        continue
    if not ok:
        all_passed = False
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}")

print()
print(f"Overall: "
      f"{'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
sys.exit(0 if all_passed else 1)
