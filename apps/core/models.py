from django.conf import settings
from django.db import models, transaction


class Sequence(models.Model):
    """Monotonic counter used to generate permanent, never-reused record IDs.

    IDs such as ``STU-000001`` / ``TCH-000001`` must never be duplicated even if a
    record is deleted. A dedicated counter row is incremented atomically inside a
    transaction so concurrent saves can never hand out the same number twice.
    """

    name = models.CharField(max_length=20, unique=True)
    next_value = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "ID Sequence"
        verbose_name_plural = "ID Sequences"

    def __str__(self):
        return f"{self.name} -> {self.next_value}"

    @classmethod
    def take_next(cls, name: str) -> int:
        """Atomically claim and return the next number for ``name``."""
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(
                name=name, defaults={"next_value": 1}
            )
            value = seq.next_value
            seq.next_value += 1
            seq.save(update_fields=["next_value"])
            return value

    @classmethod
    def ensure_above(cls, name: str, value: int) -> None:
        """Push the stored counter forward if it sits at or below ``value``.

        Used for self-healing after a database restore/import where entity rows
        exist but the counter row is missing or lagging behind them. A missing
        row is created on demand starting just above ``value``; an existing row
        is only ever moved forward, never backwards.
        """
        cls.objects.get_or_create(name=name, defaults={"next_value": value + 1})
        cls.objects.filter(name=name, next_value__lte=value).update(
            next_value=value + 1
        )


class SchoolSettings(models.Model):
    """Singleton record holding school-wide branding and contact details.

    Used by the global ``school_info`` context processor so every template (and
    every printable document header) can display the configured school name,
    phone number, and logo instead of hardcoded text.
    """

    DEFAULT_SCHOOL_NAME = "School Management System"

    school_name = models.CharField(
        max_length=120,
        default=DEFAULT_SCHOOL_NAME,
        help_text="Shown in the sidebar, page titles, login screen and all printable documents.",
    )
    school_phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Contact number printed on receipts, payslips and report letterheads.",
    )
    school_logo = models.ImageField(
        upload_to="school_logo/",
        blank=True,
        null=True,
        help_text="Logo shown next to the school name on printed documents.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "School Settings"
        verbose_name_plural = "School Settings"

    def __str__(self):
        return self.school_name

    def save(self, *args, **kwargs):
        # Singleton behaviour: every save writes to row pk=1.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SchoolSettings":
        """Return the single settings row, creating it with defaults if missing."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def get_settings(cls) -> "SchoolSettings":
        """Alias of :meth:`load` used by the school_info context processor."""
        return cls.load()

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=120, default="Notification")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"To {self.user}: {self.message[:20]}"
