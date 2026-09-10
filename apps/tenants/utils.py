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
import threading
from pathlib import Path

from django.apps import apps as _django_apps
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


# ---------------------------------------------------------------------------
# On-the-fly tenant schema verification & self-healing
# ---------------------------------------------------------------------------
# Apps whose tables live ONLY in the master (default) database and are
# therefore NOT expected inside tenant databases.
_TENANT_APP_EXCLUSIONS = frozenset({"tenants", "sessions"})

# Aliases whose schema has already been verified in THIS process.  An SQLite
# schema is stable for the lifetime of a worker process (migrations only run
# via this codebase or a redeploy), so one verification per worker per tenant
# keeps the hot path to a single lightweight query.
_VERIFIED_TENANT_ALIASES: set[str] = set()
_VERIFIED_TENANT_LOCK = threading.Lock()

_expected_tables_cache = None
_expected_tables_lock = threading.Lock()


def get_expected_tenant_tables() -> frozenset[str]:
    """Return every table a fully-migrated tenant DB must contain.

    Derived dynamically from the live model registry (``apps.get_models``) so
    the list automatically grows when new models/migrations are added to the
    project.  Master-only apps (the ``tenants`` registry and shared ``sessions``
    table) are excluded because they live exclusively in the default database.
    """
    global _expected_tables_cache
    if _expected_tables_cache is not None:
        return _expected_tables_cache
    with _expected_tables_lock:
        if _expected_tables_cache is None:
            tables = {
                model._meta.db_table
                for model in _django_apps.get_models(include_auto_created=True)
                if model._meta.app_label not in _TENANT_APP_EXCLUSIONS
            }
            _expected_tables_cache = frozenset(tables)
    return _expected_tables_cache


def _list_tenant_tables(alias: str) -> set[str]:
    """Return the names of all user tables currently in the tenant DB."""
    with connections[alias].cursor() as cur:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return {row[0] for row in cur.fetchall()}


def _recorded_migration_keys(alias: str) -> set[tuple[str, str]]:
    """Return every ``(app_label, name)`` row recorded in django_migrations."""
    with connections[alias].cursor() as cur:
        cur.execute("SELECT app, name FROM django_migrations")
        return {(app, name) for app, name in cur.fetchall()}


def _creating_migration_map(loader):
    """Map ``db_table`` -> ``(app_label, migration_name)`` that creates it.

    Built from every ``CreateModel`` operation across all migrations, so the
    repair routine can locate precisely which migration owns a missing table.
    """
    from django.db.migrations.operations.models import CreateModel

    mapping: dict[str, tuple[str, str]] = {}
    for app_label, migrations in loader.migrations.items():
        for name, migration in migrations.items():
            for op in migration.operations:
                if isinstance(op, CreateModel):
                    table = op.options.get("db_table") or (
                        f"{app_label}_{op.name.lower()}"
                    )
                    mapping.setdefault(table, (app_label, name))
    return mapping


def _resolve_repair_changes(
    alias: str, missing_tables: set[str]
) -> list[tuple[str, str]]:
    """Return the stale ``django_migrations`` rows to delete for a repair.

    For each missing table we find the migration that creates it and take the
    whole forward plan from that migration; every *recorded* row in that plan
    is removed.  Removing the full forward plan keeps migration history
    consistent (a migration never stays "applied" while its dependency is
    removed), which avoids ``InconsistentMigrationHistory`` on re-migrate.
    """
    from django.db.migrations.loader import MigrationLoader

    loader = MigrationLoader(None, ignore_no_migrations=True)
    recorded = _recorded_migration_keys(alias)
    if not recorded:
        return []

    creating = _creating_migration_map(loader)
    to_delete: set[tuple[str, str]] = set()
    unresolved: set[str] = set()

    for table in missing_tables:
        key = creating.get(table)
        if key is None:
            unresolved.add(table)
            continue
        try:
            plan = loader.graph.forwards_plan(key, include_unmigrated=False)
        except KeyError:  # pragma: no cover - migration graph should contain it
            unresolved.add(table)
            continue
        for mig in plan:
            item = (mig.app_label, mig.name)
            if item in recorded:
                to_delete.add(item)

    # Fallback for tables whose creating migration could not be identified:
    # clear the recorded history of the app that owns the table (for Django's
    # default naming the app label is the table name up to the last underscore).
    if unresolved:
        for table in unresolved:
            candidate = table.rsplit("_", 1)[0]
            for (app, name) in list(recorded):
                if app == candidate:
                    to_delete.add((app, name))

    return sorted(to_delete)


def _create_tenant_db_file(path: Path) -> None:
    """Create an empty SQLite file (mirroring provision_tenant_db permissions)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    try:
        os.chmod(path, 0o666)
    except OSError:  # pragma: no cover - non-POSIX or restricted FS
        logger.warning("Could not chmod tenant DB file %s", path)


def _repair_missing_tables(tenant, missing_tables: set[str]) -> None:
    """Clear stale history rows for the missing tables, then re-run migrate."""
    alias = tenant.db_alias
    try:
        changes = _resolve_repair_changes(alias, missing_tables)
    except Exception:  # noqa: BLE001 - django_migrations may not exist yet
        logger.exception(
            "Could not inspect migration history for tenant %s", tenant.slug
        )
        changes = []

    if changes:
        logger.warning(
            "Removing %d stale migration record(s) for tenant %s so Django can "
            "rebuild the missing tables.",
            len(changes),
            tenant.slug,
        )
        with connections[alias].cursor() as cur:
            # Tenant DBs are always SQLite (see register_tenant_db), so the
            # qmark placeholder is correct here.
            cur.executemany(
                "DELETE FROM django_migrations WHERE app = ? AND name = ?",
                changes,
            )

    migrate_tenant_db(tenant, interactive=False, verbosity=0)


def ensure_tenant_migrations(tenant, force: bool = False) -> bool:
    """Verify a tenant DB has every expected table and repair it on the fly.

    Called automatically for every tenant request by ``TenantMiddleware`` (and
    available for management contexts).  Fast path: a single ``sqlite_master``
    query per worker process per tenant.  If a critical table (e.g.
    ``teachers_teachersalary``) is missing — even when ``django_migrations``
    claims the migrations were applied — the stale history records are removed
    and ``migrate`` is re-run so the schema self-heals without manual SQL
    deletes or ad-hoc management commands.

    Returns ``True`` once the schema is complete.  Raises
    :class:`~django.db.utils.OperationalError` if the schema cannot be repaired.
    """
    from django.db.utils import OperationalError

    alias = tenant.db_alias
    if not force:
        with _VERIFIED_TENANT_LOCK:
            if alias in _VERIFIED_TENANT_ALIASES:
                return True

    register_tenant_db(tenant)

    # A Tenant row without a database file (or with a brand-new empty file) is
    # fully healed here: the file is created and migrations are applied.
    db_path = get_tenant_db_path(tenant.db_name)
    if not db_path.exists():
        _create_tenant_db_file(db_path)

    expected = get_expected_tenant_tables()
    try:
        existing = _list_tenant_tables(alias)
    except Exception:  # noqa: BLE001 - freshly created/empty file
        existing = set()

    missing = expected - existing
    if not missing:
        with _VERIFIED_TENANT_LOCK:
            _VERIFIED_TENANT_ALIASES.add(alias)
        return True

    logger.warning(
        "Tenant %s schema incomplete: %d table(s) missing (e.g. %s). "
        "Running on-the-fly migration repair...",
        tenant.slug,
        len(missing),
        ", ".join(sorted(missing)[:5]),
    )

    # Pass 1 — apply any genuinely pending migrations (e.g. tenant predates a
    # newly shipped migration).  This alone fixes most new-migration cases.
    try:
        migrate_tenant_db(tenant, interactive=False, verbosity=0)
    except Exception:  # noqa: BLE001 - continue to history repair below
        logger.error(
            "Plain migrate failed for tenant %s; attempting history repair.",
            tenant.slug,
            exc_info=True,
        )
    missing = expected - _list_tenant_tables(alias)

    # Pass 2 — tables still missing despite migration history: clear the stale
    # rows for the owning migrations and re-run migrate to rebuild the tables.
    if missing:
        try:
            _repair_missing_tables(tenant, missing)
        except Exception:  # noqa: BLE001 - keep the last-resort path available
            logger.error(
                "Migration-history repair failed for tenant %s.",
                tenant.slug,
                exc_info=True,
            )
        missing = expected - _list_tenant_tables(alias)

    # Pass 3 (last resort) — fake-apply whatever still cannot be built so the
    # tenant recovers instead of returning 500s while an operator intervenes.
    if missing:
        try:
            migrate_tenant_db(tenant, interactive=False, verbosity=0, fake=True)
        except Exception:  # noqa: BLE001 - nothing more we can do
            logger.exception(
                "Fake-apply fallback failed for tenant %s.", tenant.slug
            )
        missing = expected - _list_tenant_tables(alias)

    if missing:
        raise OperationalError(
            "Tenant DB '%s' is still missing tables after on-the-fly repair: %s"
            % (alias, ", ".join(sorted(missing)[:5]))
        )

    with _VERIFIED_TENANT_LOCK:
        _VERIFIED_TENANT_ALIASES.add(alias)
    return True


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

    # Forget any verified-schema cache entry for this tenant.
    with _VERIFIED_TENANT_LOCK:
        _VERIFIED_TENANT_ALIASES.discard(alias)

    # Close the connection if it's open
    if alias in connections:
        connections[alias].close()

    # Remove from registry
    if alias in connections.databases:
        del connections.databases[alias]

    # Delete the file
    if db_path.exists():
        os.remove(db_path)
