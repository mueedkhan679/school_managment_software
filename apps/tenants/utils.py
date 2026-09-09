"""Tenant database provisioning utilities.

Tenant database files live in ``settings.TENANT_DATABASES_DIR`` (defaults to a
sibling directory of the project so the master ``db.sqlite3`` is not cluttered
with per-tenant files).  The master tenant registry still lives in the
``default`` db.
"""

from __future__ import annotations

import logging
import os
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
      1. Register the database alias.
      2. Run ``migrate`` against the tenant's database.
      3. Create a default Admin user for the school.
    """
    register_tenant_db(tenant)
    alias = tenant.db_alias

    # Run all migrations on the tenant DB (excluding the tenants app).
    # Use fake_initial=True so the first run on a fresh SQLite database
    # records the initial state without trying to re-create tables that
    # were already built by the migrate command itself.
    call_command(
        "migrate",
        database=alias,
        verbosity=0,
        interactive=False,
        fake_initial=True,
    )

    # Create the default school admin user inside the tenant DB
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

    # Create default SchoolSettings inside the tenant DB
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
