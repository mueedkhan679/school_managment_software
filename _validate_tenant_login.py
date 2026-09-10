"""End-to-end verification of mobile-app tenant-aware login (temporary diagnostic).

Creates a throwaway tenant, provisions it, seeds a student user inside the
TENANT database, then drives the real request stack (full middleware) via
Django's test client to prove:

  1. ``X-Tenant-Slug`` header login          -> 200 + JWT + canonical school slug
  2. Legacy ``X-Tenant-Key`` header login    -> 200
  3. Body-only ``tenant`` login (no header)  -> 200
  4. No tenant identifier anywhere           -> NOT 200 (master DB has no users)
  5. Unknown School ID                       -> 400 with a clear message
  6. JWT-authenticated follow-up with header -> 200, tenant data
  7. User truly lives in the tenant DB only

Cleans up after itself (tenant row + sqlite file removed).
"""
import json
import os
import sys
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.students.models import Gender, Student
from apps.tenants.db_router import set_current_db_alias
from apps.tenants.models import Tenant
from apps.tenants.utils import delete_tenant_db, provision_tenant_db

User = get_user_model()

SLUG = f"login-verify-{int(time.time())}"
USERNAME = "verify_stu_user"
PASSWORD = "verify-pass-123"

failures = []
tenant = None


def check(label, ok, extra=""):
    suffix = f"  [{extra}]" if extra else ""
    print(f"{'PASS' if ok else 'FAIL'}  {label}{suffix}")
    if not ok:
        failures.append(label)


def login_post(client, body, **headers):
    return client.post(
        "/api/v1/auth/login/",
        data=json.dumps(body),
        content_type="application/json",
        **headers,
    )


try:
    # ---------------------------------------------------------------- setup
    tenant = Tenant.objects.create(slug=SLUG, school_name="Login Verify School")
    provision_tenant_db(tenant)
    alias = tenant.db_alias

    # Seed class + student *inside the tenant DB* (thread-local routes writes).
    set_current_db_alias(alias)
    cls = SchoolClass.objects.create(name="Verify Class", order=1)
    user = User.objects.create_user(
        username=USERNAME, password=PASSWORD, role=Role.STUDENT
    )
    student = Student.objects.create(
        name="Verify Student",
        father_name="Verify Father",
        school_class=cls,
        date_of_birth="2015-01-01",
        gender=Gender.MALE,
        user=user,
    )
    set_current_db_alias(None)
    print(f"Throwaway tenant '{SLUG}' provisioned; student {student.student_id} seeded.\n")

    client = Client()

    # --------------------------------------------------- 1. X-Tenant-Slug header
    resp = login_post(
        client,
        {"username": USERNAME, "password": PASSWORD},
        HTTP_X_TENANT_SLUG=SLUG,
    )
    ok = resp.status_code == 200
    body = resp.json() if ok else {}
    check("login with X-Tenant-Slug header returns 200", ok, f"status={resp.status_code}")
    token = ""
    if ok:
        payload = body.get("payload", {})
        token = payload.get("access", "")
        check("login payload contains JWT access token", bool(token))
        school = body.get("school") or {}
        check(
            "response includes canonical school slug",
            school.get("slug") == SLUG,
            f"school={school}",
        )
        u = payload.get("user", {})
        check(
            "login payload contains student profile info",
            bool(u.get("student_id")),
            f"student_id={u.get('student_id')}",
        )

    # --------------------------------------------------- 2. legacy X-Tenant-Key
    resp = login_post(
        client,
        {"username": USERNAME, "password": PASSWORD},
        HTTP_X_TENANT_KEY=SLUG,
    )
    check(
        "login with legacy X-Tenant-Key header returns 200",
        resp.status_code == 200,
        f"status={resp.status_code}",
    )

    # --------------------------------------------------- 3. body-only tenant
    resp = login_post(
        client,
        {"username": USERNAME, "password": PASSWORD, "tenant": SLUG},
    )
    check(
        "login with body-only 'tenant' (no header) returns 200",
        resp.status_code == 200,
        f"status={resp.status_code}",
    )

    # --------------------------------------------------- 4. no tenant at all
    resp = login_post(client, {"username": USERNAME, "password": PASSWORD})
    check(
        "login WITHOUT any tenant identifier does NOT succeed",
        resp.status_code != 200,
        f"status={resp.status_code}",
    )

    # --------------------------------------------------- 5. unknown school id
    resp = login_post(
        client,
        {"username": USERNAME, "password": PASSWORD, "tenant": "no-such-school"},
    )
    ok5 = resp.status_code == 400 and "Unknown school" in resp.json().get("message", "")
    check(
        "login with unknown School ID returns clear 400",
        ok5,
        f"status={resp.status_code}",
    )

    # --------------------------------------------------- 6. JWT follow-up GET
    resp = client.get(
        "/api/v1/students/profile/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
        HTTP_X_TENANT_SLUG=SLUG,
    )
    ok6 = resp.status_code == 200
    check(
        "JWT-authenticated profile GET with header returns 200",
        ok6,
        f"status={resp.status_code}",
    )
    if ok6:
        payload = resp.json().get("payload", {})
        check(
            "profile payload comes from the tenant DB",
            payload.get("name") == "Verify Student",
            f"name={payload.get('name')}",
        )

    # --------------------------------------------------- 7. user not in master
    check(
        "student user does NOT exist in the master database",
        not User.objects.filter(username=USERNAME).exists(),
    )

    # --------------------------------------- 8. ?tenant= query param fallback
    resp = client.post(
        f"/api/v1/auth/login/?tenant={SLUG}",
        data=json.dumps({"username": USERNAME, "password": PASSWORD}),
        content_type="application/json",
    )
    check(
        "login with ?tenant= query param returns 200",
        resp.status_code == 200,
        f"status={resp.status_code}",
    )

finally:
    # ------------------------------------------------------------- cleanup
    try:
        delete_tenant_db(tenant)
    except Exception as exc:  # noqa: BLE001
        print(f"cleanup warning: could not delete tenant db: {exc}")
    try:
        if tenant is not None:
            tenant.delete()
    except Exception:  # noqa: BLE001
        pass

print()
if failures:
    print(f"RESULT: {len(failures)} check(s) FAILED: {failures}")
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED")
