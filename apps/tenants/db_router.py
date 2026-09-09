"""
Dynamic database router for multi-tenant isolation.

Routing rules:
  * Models belonging to the ``tenants`` app always use the ``default``
    (master) database — the tenant registry must live in one central place.
  * The Django ``sessions`` app is routed to the ``default`` database
    exclusively.  All tenants share one session table, which simplifies
    provisioning (no per-tenant ``django_session`` table to create).
  * The Django ``auth``, ``contenttypes``, ``admin`` apps are routed to the
    *tenant* database when a tenant context is active, so each school gets
    its own users and admin log.  When no tenant context exists (e.g.
    master-admin views), they fall back to ``default``.
  * All other app models (``students``, ``fees``, ``attendance``, etc.) are
    routed to the active tenant's database.
  * ``allow_migrate`` scopes migrations: the ``tenants`` and ``sessions``
    apps are migrated only on ``default``; framework shared apps (``auth``,
    ``contenttypes``, ...) are migrated on *every* database (so each tenant
    DB gets its own copy); all other apps are migrated on any database that
    is NOT ``default`` (tenant databases).
"""

from __future__ import annotations

import threading
from typing import Any

# Thread-local storage set by TenantMiddleware
_thread_locals = threading.local()

# Apps whose tables must live ONLY in the master (default) database.
MASTER_APPS = frozenset({"tenants", "sessions"})

# Framework-level apps that should exist in every tenant DB (and also in
# the master DB so the super-admin login flow works there too).
SHARED_FRAMEWORK_APPS = frozenset({"auth", "contenttypes", "admin"})


def get_current_db_alias() -> str | None:
    """Return the active tenant's DB alias, or None if no tenant is set."""
    return getattr(_thread_locals, "tenant_db_alias", None)


def set_current_db_alias(alias: str | None) -> None:
    """Set the active tenant DB alias (called by TenantMiddleware)."""
    _thread_locals.tenant_db_alias = alias


class TenantRouter:
    """Routes reads and writes to the correct database based on tenant context."""

    def _route(self, model, **hints: Any) -> str:
        app_label = model._meta.app_label

        # Tenant registry and sessions always go to master.
        if app_label in MASTER_APPS:
            return "default"

        # Everything else goes to the active tenant DB (or default if none).
        tenant_db = get_current_db_alias()
        return tenant_db or "default"

    def db_for_read(self, model, **hints: Any) -> str:
        return self._route(model, **hints)

    def db_for_write(self, model, **hints: Any) -> str:
        return self._route(model, **hints)

    def allow_relation(self, obj1: Any, obj2: Any, **hints: Any) -> bool:
        """Only allow relations within the same database."""
        db1 = self._route(type(obj1))
        db2 = self._route(type(obj2))
        return db1 == db2

    def allow_migrate(self, db: str, app_label: str, model_name: str | None = None, **hints: Any) -> bool:
        """Control which models are migrated to which database.

        * ``tenants`` and ``sessions`` apps: only migrate on ``default``.
        * Shared framework apps (``auth``, ``contenttypes``, ``admin``):
          migrate on *every* database (master + each tenant DB).
        * All other apps: migrate on any database that is NOT ``default``
          (i.e. tenant databases), so the master DB stays free of
          school-scoped tables.
        """
        if app_label in MASTER_APPS:
            return db == "default"

        if app_label in SHARED_FRAMEWORK_APPS:
            # These must exist in both the master DB (for super-admin login)
            # and in each tenant DB (for tenant-scoped auth/sessions).
            return True

        # School-scoped apps only migrate onto tenant databases.
        return db != "default"