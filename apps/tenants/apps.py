"""App config for the multi-tenant engine.

Registers a ``post_migrate`` receiver so that whenever the master (``default``)
database finishes migrating, every *existing* tenant database is automatically
migrated too.  Brand-new tenants are migrated by
:func:`apps.tenants.utils.provision_tenant_db`; this receiver is the safety net
that keeps previously-created schools up to date after new migrations are
added to the project (preventing ``OperationalError: no such table`` errors).

Disable the automatic behaviour with ``DISABLE_TENANT_AUTO_MIGRATE=1``.
"""
import logging
import os

from django.apps import AppConfig
from django.db import connection
from django.db.models.signals import post_migrate, pre_save, post_save

logger = logging.getLogger("tenants.apps")

#: Env var that switches off the automatic tenant migration after a master
#: ``migrate`` (e.g. for tightly-controlled CI pipelines).
DISABLE_ENV_VAR = "DISABLE_TENANT_AUTO_MIGRATE"

_DISABLE_TRUTHY = ("1", "true", "yes", "on")


def _auto_migrate_existing_tenants(sender, using, **kwargs):
    """Apply pending migrations to every tenant DB after the master migrate."""
    # Only react to migrations performed on the master (default) database.
    # Migrating an individual tenant DB fires post_migrate with that tenant's
    # alias — that call is already handled by the per-tenant migration and must
    # not trigger a full sweep (avoids recursion).
    if using != "default":
        return

    if os.environ.get(DISABLE_ENV_VAR, "").strip().lower() in _DISABLE_TRUTHY:
        logger.info("Tenant auto-migration disabled via %s.", DISABLE_ENV_VAR)
        return

    # Never touch real tenant files while running the test-suite: Django's
    # SQLite test runner replaces the master database name with an in-memory
    # ``file:memorydb...`` database.
    default_name = str(connection.settings_dict.get("NAME", ""))
    if default_name.startswith("file:memorydb"):
        logger.debug("Skipping tenant auto-migration (test database detected).")
        return

    try:
        from apps.tenants.models import Tenant
        from apps.tenants.utils import get_tenant_db_path, migrate_tenant_db

        tenants = list(
            Tenant.objects.all().only("slug", "db_name").order_by("slug")
        )
    except Exception:  # noqa: BLE001 - tenants table may not exist yet
        logger.debug(
            "Tenant table not available yet; skipping auto-migration.",
            exc_info=True,
        )
        return

    if not tenants:
        return

    migrated = 0
    skipped = 0
    failed = []
    for tenant in tenants:
        try:
            if not get_tenant_db_path(tenant.db_name).exists():
                skipped += 1
                continue
            migrate_tenant_db(tenant, interactive=False, verbosity=0)
            migrated += 1
        except Exception:  # noqa: BLE001 - continue with the next tenant
            failed.append(tenant.slug)
            logger.exception(
                "Auto-migration failed for tenant %s.", tenant.slug
            )

    if failed or skipped:
        logger.warning(
            "Tenant auto-migration complete: %d ok, %d skipped, %d failed%s",
            migrated,
            skipped,
            len(failed),
            f" -> {', '.join(failed)}" if failed else "",
        )
    else:
        logger.info(
            "Tenant auto-migration complete: %d tenant(s) up to date.",
            migrated,
        )


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tenants"
    verbose_name = "Tenant Management"

    def ready(self):
        # Django calls ready() once per app config, so a plain connect() is
        # idempotent in practice.  Guarded anyway so repeated calls (some test
        # frameworks reload configs) never stack duplicate receivers.
        if not getattr(self, "_tenant_post_migrate_connected", False):
            post_migrate.connect(_auto_migrate_existing_tenants, sender=self)
            self._tenant_post_migrate_connected = True

        if not getattr(self, "_tenant_save_signals_connected", False):
            # Automatically provision + migrate brand-new tenant databases as soon
            # as the School/Tenant record is created (the permanent fix for missing
            # tenant tables).  See apps.tenants.signals for the implementation.
            from apps.tenants.models import Tenant
            from apps.tenants.signals import (
                _on_tenant_post_save,
                _on_tenant_pre_save,
            )

            pre_save.connect(_on_tenant_pre_save, sender=Tenant)
            post_save.connect(_on_tenant_post_save, sender=Tenant)
            self._tenant_save_signals_connected = True
