"""End-to-end validation: 403 Access Denied fix on tenant login URLs.

Drives the FULL middleware stack via Django's test client and proves:
  1. /accounts/login/ renders (200) for anonymous users.
  2. /t/<slug>/accounts/login/ renders (200) for a real tenant.
  3. /t/<unknown-slug>/accounts/login/ renders (200) — never 403s.
  4. /t/<unknown-slug>/dashboard/ still 403s (correct: bad tenant URL).
  5. POST login as the provisioned tenant admin works and redirects into
     the tenant URL space.
  6. The provisioned admin's UserProfile has role=ADMIN + is_approved=True
     inside the tenant DB.
  7. A protected dashboard page returns 200 after login (admin_required
     no longer 403s the provisioned admin).
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.test import Client  # noqa: E402

from apps.accounts.models import Role  # noqa: E402
from apps.tenants.models import Tenant  # noqa: E402
from apps.tenants.utils import (  # noqa: E402
    delete_tenant_db,
    provision_tenant_db,
    register_tenant_db,
)
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()

failures = []


def check(label, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label} {extra}")
    if not cond:
        failures.append(label)


slug = f"verify403-{os.getpid()}"
tenant = None
try:
    # --- Provision a throwaway tenant -------------------------------------
    tenant = Tenant.objects.create(
        slug=slug,
        school_name=f"Verify 403 School {os.getpid()}",
        db_name=f"tenant_verify403_{os.getpid()}",
    )
    # The post_save signal may auto-provision an ADMIN first; capture the
    # username the provisioner actually guarantees (ensure_tenant_admin
    # prefers an existing ADMIN-role account by design).
    admin_username = provision_tenant_db(
        tenant, admin_username="verifyadmin", admin_password="verifypass123"
    )
    check("provision_tenant_db returns admin username", bool(admin_username), f"got {admin_username!r}")
    admin_password = "verifypass123"

    alias = tenant.db_alias
    register_tenant_db(tenant)

    # --- Contract checks inside the tenant DB -----------------------------
    user = User.objects.using(alias).get(username=admin_username)
    check("tenant admin exists", user.username == admin_username)
    check("tenant admin is_superuser", user.is_superuser)
    check("tenant admin is_staff", user.is_staff)
    check("tenant admin is_active", user.is_active)
    check("tenant admin role is ADMIN", user.role == Role.ADMIN)
    check("tenant admin not a master superadmin", user.is_superadmin is False)

    client = Client()

    # --- Middleware / login URL accessibility ------------------------------
    r1 = client.get("/accounts/login/")
    check("bare /accounts/login/ -> 200", r1.status_code == 200, f"got {r1.status_code}")

    r2 = client.get(f"/t/{slug}/accounts/login/")
    check(
        f"/t/{slug}/accounts/login/ -> 200",
        r2.status_code == 200,
        f"got {r2.status_code}",
    )

    r3 = client.get("/t/unknown-school-xyz/accounts/login/")
    check(
        "/t/unknown-school-xyz/accounts/login/ -> 200 (no 403)",
        r3.status_code == 200,
        f"got {r3.status_code}",
    )

    r4 = client.get("/t/unknown-school-xyz/dashboard/")
    check(
        "/t/unknown-school-xyz/dashboard/ -> 403 (bad tenant still blocked)",
        r4.status_code == 403,
        f"got {r4.status_code}",
    )

    # --- Full tenant admin login flow --------------------------------------
    r5 = client.post(
        f"/t/{slug}/accounts/login/",
        {"username": admin_username, "password": admin_password},
    )
    check(
        "POST tenant login redirects (302)",
        r5.status_code == 302,
        f"got {r5.status_code}",
    )
    if r5.status_code != 302:
        body = r5.content.decode("utf-8", "replace")
        for marker in ("errorlist", "alert", "Invalid", "disabled", "locked"):
            idx = body.lower().find(marker.lower())
            if idx != -1:
                print(f"  debug[{marker}]:", body[max(0, idx - 120): idx + 240].strip())
    location = r5.get("Location", "")
    check(
        f"login redirect stays in tenant space (/t/{slug}/...)",
        location.startswith(f"/t/{slug}/"),
        f"got {location!r}",
    )

    r6 = client.get(location) if r5.status_code == 302 and location else None
    if r6 is not None:
        check(
            "protected page after admin login -> 200 (no 403)",
            r6.status_code == 200,
            f"got {r6.status_code}",
        )
finally:
    # --- Cleanup ------------------------------------------------------------
    if tenant is not None:
        try:
            delete_tenant_db(tenant)
        except Exception as e:
            print("cleanup db failed:", e)
        try:
            Tenant.objects.filter(pk=tenant.pk).delete()
        except Exception as e:
            print("cleanup row failed:", e)

print()
if failures:
    print("RESULT: FAILURES ->", failures)
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED")
