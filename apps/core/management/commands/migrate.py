"""Tenant-aware wrapper around Django's built-in ``migrate`` command."""

from django.core.management.commands.migrate import Command as DjangoMigrateCommand


class Command(DjangoMigrateCommand):
    """Register all known tenant aliases before parsing ``--database``."""

    def add_arguments(self, parser):
        self._register_tenant_databases()
        super().add_arguments(parser)

    @staticmethod
    def _register_tenant_databases():
        try:
            from apps.tenants.models import Tenant
            from apps.tenants.utils import register_tenant_db

            for tenant in Tenant.objects.using("default").only("db_name"):
                register_tenant_db(tenant)
        except Exception:
            # The first master migration runs before the Tenant table exists.
            return
