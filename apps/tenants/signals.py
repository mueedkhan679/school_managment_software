"""Automatically provision and migrate a tenant database when a new School/Tenant is created.

This is the permanent fix for "missing tenant tables": whenever a brand-new
Tenant row is saved, the system:

1. Creates the isolated SQLite database file for that tenant (``tenant_<slug>.sqlite3``).
2. Sets the router's thread-local tenant context so migrations are applied to the
   *tenant* database (not the master).
3. Calls :func:`apps.tenants.utils.migrate_tenant_db` to apply every pending
   migration to the new tenant DB.
4. Updates the Tenant's ``migration_status`` (``OK`` or ``FAILED``) and logs any
   failure traceback into ``error_log``.

All of this is wrapped in ``try/except`` so an auto-migration failure never crashes
the application — the Tenant row is still saved, but flagged as FAILED so it can be
re-provisioned manually (or retried by the post_migrate sweep in apps.py).

Design notes:
* Pre-save is used for the primary migration so that, in the common case, the tenant
  is fully ready by the time ``save()`` returns.
* A post_save receiver is also connected as a safety net / retry path: if the
  pre_save migration raised an error, the post_save receiver re-runs migration once
  more (the DB file now definitely exists, so a transient I/O failure during pre_save
  can still be recovered).  The post_save receiver intentionally skips tenants whose
  migration already succeeded to avoid redundant work.
* Both receivers only act on brand-new tenants (``instance._state.adding``) so edits
  to existing schools never trigger a re-migration.
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.tenants.models import Tenant

logger = logging.getLogger("tenants.signals")


def _truncate_traceback(exc: BaseException, limit: int = 4000) -> str:
    """Return a bounded plain-text traceback for storage in ``Tenant.error_log``."""
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    text = "".join(tb)
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return text


def _run_tenant_migration(tenant: Tenant) -> None:
    """Provision (if needed) + migrate the given tenant's database.

    Raises on unrecoverable failure so the caller can mark the tenant FAILED.
    """
    from apps.tenants.db_router import set_current_db_alias
    from apps.tenants.utils import get_tenant_db_path, migrate_tenant_db

    db_path = get_tenant_db_path(tenant.db_name)

    # 1) Ensure the tenant SQLite file exists (create empty file if missing).
    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()

    # 2) Route migration commands to the tenant database, not the master.
    set_current_db_alias(tenant.db_alias)

    # 3) Apply every pending migration to the tenant DB.
    #    migrate_tenant_db() is a thin wrapper around call_command('migrate', ...)
    #    scoped to this tenant's alias, so no management command output is required.
    migrate_tenant_db(tenant, interactive=False, verbosity=0)


@receiver(pre_save, sender=Tenant)
def _on_tenant_pre_save(sender, instance, **kwargs):
    """Provision + migrate the tenant DB the moment a new school is created."""
    # Only brand-new tenants need provisioning.  Edits to existing schools must
    # never re-run migration (and must not reset error_log / status).
    if not instance._state.adding:
        return

    # Default status for a brand-new tenant: PROVISIONING while we work.
    instance.migration_status = "PROVISIONING"
    instance.error_log = ""

    try:
        _run_tenant_migration(instance)
    except Exception as exc:  # noqa: BLE001 - log + flag, never crash the request
        logger.exception(
            "Auto-migration failed for new tenant %s (%s).",
            instance.slug,
            instance.db_name,
        )
        instance.migration_status = "FAILED"
        instance.error_log = _truncate_traceback(exc)
    else:
        logger.info(
            "Auto-migration succeeded for new tenant %s (%s).",
            instance.slug,
            instance.db_name,
        )
        instance.migration_status = "OK"


@receiver(post_save, sender=Tenant)
def _on_tenant_post_save(sender, instance, created, **kwargs):
    """Safety-net retry + status reconciliation after a Tenant is saved."""
    # No-op for existing schools and for tenants that already provisioned OK.
    if not created:
        return
    if instance.migration_status == "OK":
        return

    # If the pre_save migration failed (or was skipped), retry once here.  By this
    # point the Tenant row is committed, so the DB file definitely exists.
    if instance.migration_status == "FAILED":
        try:
            _run_tenant_migration(instance)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Retry auto-migration still failed for tenant %s (%s).",
                instance.slug,
                instance.db_name,
            )
            # Persist the (possibly updated) failure traceback.
            instance.error_log = _truncate_traceback(exc)
            instance.save(update_fields=["migration_status", "error_log", "updated_at"])
            return

        instance.migration_status = "OK"
        instance.error_log = ""
        instance.save(update_fields=["migration_status", "error_log", "updated_at"])
        logger.info(
            "Retry auto-migration succeeded for tenant %s (%s).",
            instance.slug,
            instance.db_name,
        )
