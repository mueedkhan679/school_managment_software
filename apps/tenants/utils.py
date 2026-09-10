"""Tenant database provisioning utilities.

Tenant database files live in ``settings.TENANT_DATABASES_DIR`` (defaults to a
sibling directory of the project so the master ``db.sqlite3`` is not cluttered
with per-tenant files).  The master tenant registry still lives in the
``default`` db.
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import connections

logger = logging.getLogger("tenants.utils")


def get_tenant_db_dir() -> Path:
    """Return (and create if needed) the directory holding tenant SQLite files."""
    d = Path(settings.TENANT_DATABASES_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_tenant_db_path(db_name: str) -> Path:
    """Return the full filesystem path for a tenant's SQLite database."""
    return get_tenant_db_dir() / f"{db_name}.sqlite3"


def with_tenant_prefix(path: str, request=None) -> str:
    """Ensure a path is prefixed with the active tenant's ``/t/<slug>/`` prefix.

    ``reverse()`` may resolve app names through the generic ``/t/`` tenant
    include (registered before the catch-all ``''`` include), producing paths
    like ``/t/dashboard/``.  This helper strips that generic ``/t`` prefix and,
    when ``request.tenant`` is set, re-prefixes with the real ``/t/<slug>/``.

    Absolute URLs (``http://``, ``https://``, ``//``) and paths already inside
    the tenant's URL space are returned unchanged.
    """
    tenant = getattr(request, "tenant", None) if request is not None else None
    prefix = f"/t/{tenant.slug}/" if tenant is not None else None

    # Already correctly prefixed — leave it alone.
    if prefix is not None and path.startswith(prefix):
        return path

    # Strip the generic /t/ prefix (from reverse() resolving via the t/ include).
    if path.startswith("/t/"):
        path = path[2:]

    if tenant is None:
        return path

    return f"/t/{tenant.slug}{path}"


def register_tenant_db(tenant) -> None:
    """Dynamically register a tenant's database alias in Django's connection handler.

    This is safe to call multiple times — if the alias is already registered
    it will be a no-op.
    """
    alias = tenant.db_alias
    if alias in connections.databases:
        return

    db_path = get_tenant_db_path(tenant.db_name)

    connections.databases[alias] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(db_path),
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "OPTIONS": {},
        "TIME_ZONE": None,
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }


def provision_tenant_db(tenant):
    """Create and fully migrate a new tenant database.

    Steps:
      1. Ensure all connections are closed.
      2. Wipe any pre-existing DB file to avoid locks and "table already exists".
      3. Set permissions.
      4. Run migrations cleanly.
      5. Seed Admin and SchoolSettings.
    """
    register_tenant_db(tenant)
    alias = tenant.db_alias
    db_path = get_tenant_db_path(tenant.db_name)
    db_dir = db_path.parent
    main_db = Path(settings.DATABASES['default']['NAME'])

    # 1. Close connections
    connections[alias].close()
    connections['default'].close()

    # 2. Fresh start: wipe the file
    if db_path.exists():
        db_path.unlink()

    # 3. Permissions
    db_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(db_dir, 0o777)
    db_path.touch()
    os.chmod(db_path, 0o666)
    if main_db.exists():
        os.chmod(main_db, 0o666)

    # 4. Migrate cleanly with direct SQLite table existence check
    settings.DATABASES[alias]['OPTIONS'] = {'timeout': 30}
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students_studentacademichistory';")
        table_exists = cursor.fetchone()
        conn.close()

        if not table_exists:
            call_command('migrate', database=alias, interactive=False, verbosity=0)
        else:
            # If the table already exists, fake-apply migrations to sync state safely
            call_command('migrate', database=alias, interactive=False, fake=True, verbosity=0)
            
    finally:
        connections[alias].close()
        connections['default'].close()

    # 5. Seed Admin and SchoolSettings
    from apps.accounts.models import Role
    from django.contrib.auth import get_user_model
    User = get_user_model()

    admin_username = f"admin_{tenant.slug.replace('-', '_')}"
    if not User.objects.using(alias).filter(username=admin_username).exists():
        admin_user = User(
            username=admin_username,
            role=Role.ADMIN,
            is_staff=True,
            is_active=True,
        )
        admin_user.set_password("changeme123")
        admin_user.save(using=alias)

    from apps.core.models import SchoolSettings
    if not SchoolSettings.objects.using(alias).filter(pk=1).exists():
        SchoolSettings.objects.using(alias).create(
            pk=1,
            school_name=tenant.school_name,
            school_phone=tenant.admin_phone,
        )

    return admin_username


def delete_tenant_db(tenant):
    """Remove a tenant's database file from disk."""
    db_path = get_tenant_db_path(tenant.db_name)
    alias = tenant.db_alias

    # Close the connection if it's open
    if alias in connections:
        connections[alias].close()

    # Remove from registry
    if alias in connections.databases:
        del connections.databases[alias]

    # Delete the file
    if db_path.exists():
        os.remove(db_path)
