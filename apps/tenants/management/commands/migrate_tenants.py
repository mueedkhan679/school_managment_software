"""``python manage.py migrate_tenants`` — apply pending migrations to tenants.

Run this after deploying new migrations so every existing school database is
brought up to date.  This prevents ``OperationalError: no such table`` errors
(e.g. ``teachers_teachersalary``) on schools that were provisioned before the
new migrations existed.

Usage::

    python manage.py migrate_tenants
    python manage.py migrate_tenants --tenant demo-school
    python manage.py migrate_tenants --fake
"""
import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from apps.tenants.models import Tenant
from apps.tenants.utils import get_tenant_db_path, migrate_tenant_db

logger = logging.getLogger("tenants.management")


class Command(BaseCommand):
    help = (
        "Apply all pending database migrations to every tenant database "
        "(or a single one with --tenant)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            dest="tenant_slug",
            default=None,
            help="Only migrate the tenant database with this slug.",
        )
        parser.add_argument(
            "--fake",
            action="store_true",
            default=False,
            help=(
                "Record migrations as applied without running the SQL. "
                "Use with care."
            ),
        )

    def handle(self, *args, **options):
        tenant_slug = (options.get("tenant_slug") or "").strip() or None
        fake = bool(options.get("fake"))

        if tenant_slug:
            try:
                tenants = [Tenant.objects.get(slug=tenant_slug)]
            except Tenant.DoesNotExist:
                raise CommandError(f"No tenant found with slug '{tenant_slug}'.")
        else:
            tenants = list(Tenant.objects.order_by("slug"))

        if not tenants:
            self.stdout.write(self.style.WARNING("No tenants found to migrate."))
            return

        label = " (fake)" if fake else ""
        self.stdout.write(
            f"Migrating {len(tenants)} tenant database(s){label} ..."
        )

        migrated = 0
        skipped = 0
        failed = []
        for tenant in tenants:
            db_path = get_tenant_db_path(tenant.db_name)
            if not db_path.exists():
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[SKIP] {tenant.slug}: database file missing "
                        f"({db_path.name})"
                    )
                )
                continue

            try:
                migrate_tenant_db(tenant, interactive=False, verbosity=1, fake=fake)
                migrated += 1
                self.stdout.write(self.style.SUCCESS(f"[OK]   {tenant.slug}"))
            except Exception as exc:  # noqa: BLE001 - report and continue
                failed.append(tenant.slug)
                logger.exception("migrate_tenants failed for %s", tenant.slug)
                self.stderr.write(self.style.ERROR(f"[FAIL] {tenant.slug}: {exc}"))
            finally:
                alias = tenant.db_alias
                if alias in connections:
                    try:
                        connections[alias].close()
                    except Exception:  # noqa: S110
                        pass

        summary = (
            f"\nMigrated {migrated} of {len(tenants)} tenant database(s) "
            "successfully."
        )
        if skipped:
            summary += f" ({skipped} skipped — database file missing)"
        self.stdout.write(self.style.SUCCESS(summary))

        if failed:
            self.stderr.write(
                self.style.ERROR(f"Failed tenants: {', '.join(failed)}")
            )
            raise CommandError("One or more tenant databases failed to migrate.")