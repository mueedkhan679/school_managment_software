"""Tenant registry model — lives exclusively in the master (default) database."""

from django.db import models
from django.utils.text import slugify


class Tenant(models.Model):
    """Represents a single school tenant on the SaaS platform.

    Each Tenant row maps to an isolated database that holds all of
    the school's operational data (students, fees, attendance, etc.).
    The Tenant table itself lives only in the master/default database.
    """

    slug = models.SlugField(
        max_length=60,
        unique=True,
        help_text="URL-safe identifier (e.g. 'al-huda-academy'). Used in /t/<slug>/…",
    )
    school_name = models.CharField(
        max_length=150,
        help_text="Display name shown in the master dashboard.",
    )
    db_name = models.CharField(
        max_length=120,
        unique=True,
        editable=False,
        help_text="Auto-generated database filename/alias for this tenant.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Kill Switch — when False, all requests for this tenant return a Suspended page.",
    )
    is_locked = models.BooleanField(
        default=False,
        help_text="Lock school portal — when True, users are blocked and see a custom message.",
    )
    admin_email = models.EmailField(blank=True, default="")
    admin_phone = models.CharField(max_length=20, blank=True, default="")
    max_students = models.PositiveIntegerField(
        default=500,
        help_text="Optional student quota for this school.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Migration/lifecycle tracking — set by the auto-provision signal.
    migration_status = models.CharField(
        max_length=20,
        default="PENDING",
        choices=[
            ("PENDING", "Pending"),
            ("PROVISIONING", "Provisioning"),
            ("OK", "OK"),
            ("FAILED", "Failed"),
        ],
        editable=False,
        help_text=(
            "Auto-migration status of the tenant database. "
            "PROVISIONING = migration in progress; OK = schema up to date; "
            "FAILED = the last auto-migration raised an unhandled error."
        ),
    )
    error_log = models.TextField(
        blank=True,
        default="",
        editable=False,
        help_text="Last auto-migration failure traceback (plain text).",
    )

    class Meta:
        ordering = ["school_name"]
        verbose_name = "Tenant School"
        verbose_name_plural = "Tenant Schools"

    def __str__(self):
        status = "Active" if self.is_active else "Suspended"
        return f"{self.school_name} ({self.slug}) [{status}]"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.school_name)
        if not self.db_name:
            self.db_name = f"tenant_{self.slug.replace('-', '_')}"
        super().save(*args, **kwargs)

    @property
    def db_alias(self) -> str:
        """The Django database alias used by the router."""
        return self.db_name

    @property
    def db_filename(self) -> str:
        """Full SQLite filename for this tenant."""
        return f"{self.db_name}.sqlite3"
