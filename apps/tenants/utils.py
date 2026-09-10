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
        "OPTIONS": {
            # Avoid "database is locked" errors while the DB is being
            # migrated/heavily written (configured for every tenant).
            "timeout": 30,
        },
        "TIME_ZONE": None,
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }


def migrate_tenant_db(tenant, interactive=False, verbosity=1, fake=False):
    """Apply all pending Django migrations to a tenant's database.

    Runs ``migrate`` against ``tenant.db_alias`` so every school-scoped table
    (students, teachers, fees, attendance, classrooms, ...) as well as the
    shared framework tables (auth, contenttypes, admin) are created or updated
    inside that tenant's SQLite file.  New tenants call this automatically from
    :func:`provision_tenant_db`; existing tenants can be caught up with the
    ``migrate_tenants`` management command or after a master ``migrate`` via the
    ``post_migrate`` receiver in ``apps.tenants.apps``.

    Raises on hard migration errors (after attempting the ``--fake`` fallback
    used for pre-existing table collisions); always closes the connection.

    Returns ``True`` on success.
    """
    register_tenant_db(tenant)
    alias = tenant.db_alias
    try:
        call_command(
            "migrate",
            database=alias,
            interactive=interactive,
            verbosity=verbosity,
            fake=fake,
        )
    except Exception as exc:
        if fake:
            raise
        if "already exists" in str(exc).lower():
            # Collision from an earlier half-created schema — record the
            # remaining migrations as applied without re-running the DDL.
            logger.warning(
                "Table collision during migrate for tenant %s; fake-applying "
                "remaining migrations.",
                tenant.slug,
            )
            call_command(
                "migrate",
                database=alias,
                interactive=False,
                fake=True,
                verbosity=verbosity,
            )
        else:
            logger.exception(
                "migrate_tenant_db failed for tenant %s (%s)", tenant.slug, alias
            )
            raise
    finally:
        if alias in connections:
            connections[alias].close()
    return True


def ensure_tenant_admin(tenant, admin_username=None, admin_password=None):
    """Guarantee the tenant DB contains an enabled ADMIN-role User record.

    The tenant portal authorizes administrators through ``request.user.role``
    (see ``apps/accounts/decorators.py`` — a missing/broken role record leads
    to a 403 Access Denied).  This helper eliminates that failure mode so that
    every tenant created or managed from the Master Admin panel always has a
    local admin account:

    * If an ADMIN-role user already exists in the tenant DB it is returned; its
      password is only changed when ``admin_password`` is explicitly supplied.
    * Otherwise the user ``admin_<slug>`` (or ``admin_username``) is created
      inside the tenant database with ``role=ADMIN``, ``is_staff=True`` and
      ``is_active=True``, using ``admin_password`` (or the configured default).

    Returns the admin :class:`django.contrib.auth.models.User` instance.
    """
    from apps.accounts.models import Role
    from django.contrib.auth import get_user_model

    User = get_user_model()

    register_tenant_db(tenant)
    alias = tenant.db_alias

    if not admin_username:
        admin_username = f"admin_{tenant.slug.replace('-', '_')}"

    # Prefer any existing ADMIN-role account (handles custom naming schemes).
    admin = (
        User.objects.using(alias).filter(role=Role.ADMIN).order_by("id").first()
    )
    if admin is None:
        # A record may exist under the requested username but with a
        # broken/empty role — adopt and repair it instead of duplicating.
        admin = (
            User.objects.using(alias)
            .filter(username__iexact=admin_username)
            .first()
        )

    if admin is None:
        admin = User(username=admin_username)

    # Force the attributes the authorization layer depends on.
    admin.role = Role.ADMIN
    admin.is_staff = True
    admin.is_active = True

    if admin_password:
        admin.set_password(admin_password)
    elif not admin.password or admin.password.startswith("!"):
        # Unusable/empty password → fall back to the configured default.
        admin.set_password(
            getattr(settings, "MASTER_DEFAULT_ADMIN_PASSWORD", "changeme123")
        )

    admin.save(using=alias)
    return admin


def provision_tenant_db(tenant, admin_username=None, admin_password=None):
    """Create and fully migrate a new tenant database.

    Steps:
      1. Ensure all connections are closed.
      2. Wipe any pre-existing DB file to avoid locks and "table already exists".
      3. Set permissions.
      4. Run migrations cleanly.
      5. Seed Admin and SchoolSettings using the provided credentials.

    ``admin_username`` and ``admin_password`` allow the Master Admin to choose
    custom credentials for the school's initial admin account.  When omitted the
    classic defaults (``admin_<slug>`` / ``MASTER_DEFAULT_ADMIN_PASSWORD``) are
    used so existing callers keep working.
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

    # 4. Apply every migration to the fresh database. This runs
    #    ``call_command("migrate", database=<alias>)`` so ALL tables are fully
    #    created — students, teachers (incl. teacher salaries), fees,
    #    attendance, classrooms, accounts, plus the shared framework tables.
    migrate_tenant_db(tenant, interactive=False, verbosity=0)
    connections['default'].close()

    # 5. Seed the ADMIN user and SchoolSettings.
    # The ADMIN-role user is created explicitly inside the tenant DB so the
    # tenant portal can always authenticate/authorize an administrator
    # (no 403 Access Denied from a missing local user/role record).
    admin_username = ensure_tenant_admin(
        tenant,
        admin_username=admin_username or None,
        admin_password=admin_password or None,
    ).username

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
