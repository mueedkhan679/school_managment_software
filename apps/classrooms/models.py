from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class SchoolClass(models.Model):
    """A grade/class level: Playgroup, Nursery, KG, Class 1 ... Class 12."""

    name = models.CharField(max_length=50, unique=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    monthly_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Standard monthly tuition fee for students of this class",
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Class"
        verbose_name_plural = "Classes"

    def __str__(self):
        return self.name

    @property
    def yearly_fee(self) -> Decimal:
        """Yearly expected fee = monthly fee x 12 (automatic)."""
        return self.monthly_fee * 12

    @property
    def student_count(self) -> int:
        return self.students.count()

