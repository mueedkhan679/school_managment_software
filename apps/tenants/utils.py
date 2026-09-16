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
from django.db.utils import OperationalError

logger = logging.getLogger("tenants.utils")


# ---------------------------------------------------------------------------
# Default credentials for the initial admin superuser created inside every
# newly-provisioned tenant database.
#
# Kept in one place so the whole provisioning path (pre_save signal,
# ``provision_tenant_db()``, the management command, and direct shell calls)
# consistently produces a tenant admin that can actually pass Django's auth and
# the project's role-based authorization layer on first login.
#
# Default: ``admin`` / ``adminpassword123`` (requested baseline).  Override via
# ``settings.MASTER_ADMIN_USERNAME`` / ``settings.MASTER_ADMIN_PASSWORD``.
# ---------------------------------------------------------------------------
ADMIN_USERNAME = getattr(settings, "MASTER_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = getattr(settings, "MASTER_ADMIN_PASSWORD", "adminpassword123")


def set_default_admin_user_credentials(user: "User", role_model: type) -> None:
    """Force every flag the authorization layer depends on for an admin user.

    Django's ORM does **not** auto-set ``is_superuser`` when creating a normal
    ``User`` (even with ``role=ADMIN``), and the project's role-based decorators
    plus any superuser-gated view will return **403 Access Denied** on first
    login when that flag is left at the model default.  This helper guarantees
    a fully-powered tenant admin regardless of how the user object was built.
    """
    user.role = role_model.ADMIN
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    # Tenant admins must NOT be able to reach the master ``/master-admin/``
    # portal, so they are never marked as the master superadmin.
    user.is_superadmin = False


def get_tenant_db_dir() -> Path:
    """Return (and create if needed) the directory holding tenant SQLite files."""
    d = Path(settings.TENANT_DATABASES_DIR).expanduser()
    if not d.is_absolute():
        d = Path(settings.BASE_DIR) / d
    # resolve() gives SQLite and Django's connection registry the same absolute
    # filename on local development and PythonAnywhere worker processes.
    d = d.resolve()
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o775)
    except OSError:
        # Hosting providers can manage permissions/ACLs themselves; creation
        # may still be allowed even when chmod is not.
        logger.debug("Could not chmod tenant database directory %s", d)
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


def _prepare_sqlite_path(path: Path) -> None:
    """Ensure the SQLite parent directory and file are writable by the app."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o775)
    except OSError:
        logger.debug("Could not chmod SQLite directory %s", path.parent)
    if not path.exists():
        path.touch()
    try:
        os.chmod(path, 0o664)
    except OSError:
        logger.debug("Could not chmod SQLite file %s", path)


def register_tenant_db(tenant) -> None:
    """Dynamically register a tenant's database alias in Django's connection handler.

    This is safe to call multiple times — if the alias is already registered
    it will be a no-op.
    """
    alias = tenant.db_alias
    db_path = get_tenant_db_path(tenant.db_name)

    config = {
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

    existing = connections.databases.get(alias)
    if existing and existing.get("NAME") == config["NAME"]:
        return

    # Replace a stale registration immediately; workers must not require a
    # reload before they can use a newly created or restored tenant database.
    if alias in connections:
        connections[alias].close()
    # Keep both Django's live connection handler and the settings registry in
    # sync.  The latter matters for management commands invoked in this worker.
    settings.DATABASES[alias] = config
    connections.databases[alias] = config
    with _VERIFIED_TENANT_LOCK:
        _VERIFIED_TENANT_ALIASES.discard(alias)


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
                if (
                    model._meta.app_label not in _TENANT_APP_EXCLUSIONS
                    and model._meta.managed
                )
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
    # Django stores discovered migration modules in ``disk_migrations`` as a
    # flat ``(app_label, migration_name) -> Migration`` mapping.
    for (app_label, name), migration in loader.disk_migrations.items():
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
    _prepare_sqlite_path(path)


def _repair_missing_tables(tenant, missing_tables: set[str]) -> None:
    """Rebuild missing tenant-app tables from real migrations, never ``--fake``.

    An implicit M2M table such as ``teachers_teacher_assigned_classes`` has no
    separate ``CreateModel`` operation, so it is repaired through its owning
    app's genuine migration history.
    """
    alias = tenant.db_alias
    try:
        from django.db.migrations.loader import MigrationLoader

        creating = _creating_migration_map(
            MigrationLoader(None, ignore_no_migrations=True)
        )
        table_owners = {
            model._meta.db_table: model._meta.app_label
            for model in _django_apps.get_models(include_auto_created=True)
            if model._meta.app_label not in _TENANT_APP_EXCLUSIONS
        }
        installed_labels = {
            config.label for config in _django_apps.get_app_configs()
        }
        affected_apps = set()
        for table in missing_tables:
            migration_key = creating.get(table)
            if migration_key is not None:
                affected_apps.add(migration_key[0])
                continue
            # Implicit M2M tables are represented by an auto-created model,
            # not by a standalone CreateModel migration operation.
            app_label = table_owners.get(table)
            if app_label in installed_labels:
                affected_apps.add(app_label)
    except Exception:  # noqa: BLE001 - django_migrations may not exist yet
        logger.exception(
            "Could not inspect migration history for tenant %s", tenant.slug
        )
        affected_apps = set()

    for app_label in sorted(affected_apps):
        logger.warning(
            "Rebuilding missing %s tables for tenant %s from real migrations.",
            app_label,
            tenant.slug,
        )
        with connections[alias].cursor() as cur:
            cur.execute("DELETE FROM django_migrations WHERE app = ?", [app_label])
        call_command(
            "migrate",
            app_label,
            database=alias,
            interactive=False,
            verbosity=0,
            run_syncdb=True,
        )

    migrate_tenant_db(tenant, interactive=False, verbosity=0, run_syncdb=True)


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
    # Register before consulting the verification cache: registration may have
    # replaced an old database file under the same alias and clears that cache.
    register_tenant_db(tenant)
    db_path = get_tenant_db_path(tenant.db_name)
    # A cached verification is not valid if the SQLite file was removed or a
    # deployment restored it between requests.
    if not db_path.exists():
        with _VERIFIED_TENANT_LOCK:
            _VERIFIED_TENANT_ALIASES.discard(alias)
        _create_tenant_db_file(db_path)
    if not force:
        with _VERIFIED_TENANT_LOCK:
            if alias in _VERIFIED_TENANT_ALIASES:
                return True

    # A Tenant row without a database file (or with a brand-new empty file) is
    # fully healed here: the file is created and migrations are applied.
    expected = get_expected_tenant_tables()
    try:
        existing = _list_tenant_tables(alias)
    except Exception:  # noqa: BLE001 - freshly created/empty file
        existing = set()

    missing = expected - existing
    if not missing:
        _ensure_tenant_seed_data(tenant)
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
            # A fake migration can leave django_migrations claiming that the
            # teachers app exists while its tables are absent.  A final real
            # sync is slower but restores the schema truthfully.
            migrate_tenant_db(
                tenant, interactive=False, verbosity=0, run_syncdb=True
            )
        except Exception:  # noqa: BLE001 - nothing more we can do
            logger.exception(
                "Final real migration sync failed for tenant %s.", tenant.slug
            )
        missing = expected - _list_tenant_tables(alias)

    if missing:
        raise OperationalError(
            "Tenant DB '%s' is still missing tables after on-the-fly repair: %s"
            % (alias, ", ".join(sorted(missing)[:5]))
        )

    _ensure_tenant_seed_data(tenant)
    with _VERIFIED_TENANT_LOCK:
        _VERIFIED_TENANT_ALIASES.add(alias)
    return True


def migrate_tenant_db(
    tenant, interactive=False, verbosity=1, fake=False, run_syncdb=True
):
    """Apply all pending Django migrations to a tenant's database.

    Runs ``migrate`` against ``tenant.db_alias`` so every school-scoped table
    (students, teachers, fees, attendance, classrooms, ...) as well as the
    shared framework tables (auth, contenttypes, admin) are created or updated
    inside that tenant's SQLite file.  New tenants call this automatically from
    :func:`provision_tenant_db`; existing tenants can be caught up with the
    ``migrate_tenants`` management command or after a master ``migrate`` via the
    ``post_migrate`` receiver in ``apps.tenants.apps``.

    Uses ``fake_initial`` so existing initial tables are recognized.  If a
    legacy tenant still reports a duplicate table during a later migration,
    the migration history is fake-applied as a recovery step; the schema
    verification pass will then rebuild any genuinely missing tables.
    Always closes the connection.

    Returns ``True`` on success.
    """
    register_tenant_db(tenant)
    alias = tenant.db_alias
    _prepare_sqlite_path(get_tenant_db_path(tenant.db_name))
    try:
        call_command(
            "migrate",
            database=alias,
            interactive=interactive,
            verbosity=verbosity,
            fake=fake,
            fake_initial=True,
            run_syncdb=run_syncdb,
        )
    except OperationalError as exc:
        if fake:
            raise
        if "already exists" in str(exc).lower():
            # Older tenant databases can contain a table from a migration
            # whose django_migrations row was lost.  Do not let that legacy
            # collision abort tenant creation; ensure_tenant_migrations()
            # verifies the resulting schema and repairs missing tables.
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
                fake_initial=True,
                verbosity=verbosity,
                run_syncdb=run_syncdb,
            )
        else:
            logger.exception(
                "migrate_tenant_db failed for tenant %s (%s)", tenant.slug, alias
            )
            raise
    except Exception:
        logger.exception(
            "migrate_tenant_db failed for tenant %s (%s)", tenant.slug, alias
        )
        raise
    finally:
        if alias in connections:
            connections[alias].close()
    return True


def initialize_tenant_database(tenant) -> bool:
    """Create, migrate, verify, and seed a tenant database idempotently.

    This is the last-resort recovery entry point used by request middleware.
    It deliberately never deletes an existing database: a transient failed
    verification must repair a new/partial schema, not destroy school data.
    """
    alias = tenant.db_alias
    with _VERIFIED_TENANT_LOCK:
        _VERIFIED_TENANT_ALIASES.discard(alias)

    register_tenant_db(tenant)
    db_path = get_tenant_db_path(tenant.db_name)
    if not db_path.exists():
        _create_tenant_db_file(db_path)

    migrate_tenant_db(tenant, interactive=False, verbosity=0)
    return ensure_tenant_migrations(tenant, force=True)


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
        admin_username = ADMIN_USERNAME

    # Prefer any existing ADMIN-role account (handles custom naming schemes),
    # then fall back to the requested username — and finally to the classic
    # ``admin`` account so a freshly-provisioned tenant always has a plain
    # ``admin`` superuser (requested default: admin / adminpassword123).
    admin = (
        User.objects.using(alias).filter(role=Role.ADMIN).order_by("id").first()
    )
    if admin is None:
        admin = User.objects.using(alias).filter(username__iexact=admin_username).first()
    if admin is None and admin_username is None:
        # Provisioning default: a single ``admin`` superuser per tenant DB.
        admin = User.objects.using(alias).filter(username__iexact="admin").first()
    if admin is None:
        admin = User(username=admin_username or "admin")

    if admin_password:
        admin.set_password(admin_password)
    elif not admin.password or admin.password.startswith("!"):
        # Unusable/empty password -> fall back to the configured default
        # (requested default: admin / adminpassword123).
        admin.set_password(ADMIN_PASSWORD)

    # Force every flag the authorization layer depends on (idempotent helper).
    # Without this a brand-new tenant admin would be left with
    # ``is_superuser=False`` and return 403 Access Denied on first login.
    set_default_admin_user_credentials(admin, Role)

    # Persist the role + credential flags in the tenant database so the
    # TenantBackend lookups and the role-based decorators (``role_required`` /
    # ``admin_required``) can authorise the user on login across all tenant
    # subdomains.  The project's role-mapping layer is the User model itself
    # (with ``role`` and ``is_superadmin`` fields), so every flag must be
    # written to the tenant DB underneath ``using(alias)``.
    admin.save(using=alias)

    # Re-fetch committed record from the tenant DB so callers (and later login
    # requests) always see the authoritative role + credential flags stored in
    # the tenant database (not any in-memory template that may differ).
    return User.objects.using(alias).get(pk=admin.pk)


def _ensure_tenant_seed_data(tenant) -> None:
    """Ensure a migrated tenant can be used immediately after creation.

    Migrations create tables but not the tenant admin or singleton settings
    row.  This idempotent step is shared by creation-time provisioning and
    request-time verification.
    """
    from apps.core.models import SchoolSettings

    alias = tenant.db_alias
    ensure_tenant_admin(tenant)
    SchoolSettings.objects.using(alias).get_or_create(
        pk=1,
        defaults={
            "school_name": tenant.school_name,
            "school_phone": tenant.admin_phone,
        },
    )


def _validate_admin_provisioning_contract():
    """Lightweight runtime assertion that the admin provisioning contract is intact.

    Inspects the *source code* of ``ensure_tenant_admin`` and its flag-setting
    helper ``set_default_admin_user_credentials`` so a regression (e.g. someone
    dropping the ``is_superuser=True`` assignment) fails loudly at import time
    instead of surfacing as a 403 Access Denied at runtime.
    """
    import inspect

    expected_markers = [
        # set_default_admin_user_credentials — the authorization flags
        "is_superuser = True",
        "is_staff = True",
        "is_active = True",
        "is_superadmin = False",
        "user.role = role_model.ADMIN",
        # ensure_tenant_admin — persistence inside the tenant database
        "set_default_admin_user_credentials(admin, Role)",
        "admin.save(using=alias)",
        "User.objects.using(alias).get(pk=admin.pk)",
    ]
    source = inspect.getsource(ensure_tenant_admin) + "\n" + inspect.getsource(
        set_default_admin_user_credentials
    )
    missing = [kw for kw in expected_markers if kw not in source]
    if missing:
        raise RuntimeError(
            "Tenant admin provisioning contract is broken. "
            f"Missing contract markers: {missing}. "
            "Fix apps/tenants/utils.py:ensure_tenant_admin before deploying."
        )
    logger.info(
        "Tenant admin provisioning contract validated: is_superuser, is_staff, "
        "is_active, is_superadmin=False, role=ADMIN, admin.save(using=alias), "
        "and tenant-DB re-fetch are all present."
    )


# This source-level assertion is useful during development, but it must never
# make a deployment unavailable.  ``utils`` is imported while Django creates
# the WSGI application, so raising here turns an implementation diagnostic
# into a site-wide startup outage (notably on PythonAnywhere).
#
# Keep the check as a logged diagnostic; provisioning itself still validates
# and writes the required admin flags when it runs.
try:
    _validate_admin_provisioning_contract()
except Exception:  # noqa: BLE001 - import-time validation must be non-fatal
    logger.exception(
        "Tenant admin provisioning contract validation failed during import; "
        "continuing startup. Review ensure_tenant_admin before provisioning "
        "new tenants."
    )




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

    # 2. Fresh start: close, make the file removable, then wipe it.
    if db_path.exists():
        try:
            os.chmod(db_path, 0o664)
        except OSError:
            pass
        db_path.unlink()

    # 3. Permissions
    _prepare_sqlite_path(db_path)
    if main_db.exists():
        try:
            os.chmod(main_db, 0o664)
        except OSError:
            logger.debug("Could not chmod master database %s", main_db)

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
