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

