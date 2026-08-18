from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.constants import MONTHS
from apps.students.models import Student


class FeeStatus(models.TextChoices):
    PAID = "PAID", "Paid"
    PENDING = "PENDING", "Pending"


class StudentFee(models.Model):
    """A fee payment made by a student (counts as income).

    A duplicate payment for the same student + month + year is prevented at the
    database level unless ``is_extra`` is explicitly set, which satisfies the
    requirement that duplicates only ever happen when the admin allows them.
    """

    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="fees"
    )
    fee_month = models.PositiveSmallIntegerField(choices=MONTHS, verbose_name="Fee Month")
    fee_year = models.PositiveSmallIntegerField(verbose_name="Fee Year")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_date = models.DateField()
    status = models.CharField(
        max_length=10, choices=FeeStatus.choices, default=FeeStatus.PAID
    )
    reference = models.CharField(
        max_length=50, blank=True, help_text="Receipt/payment reference number if required"
    )
    is_extra = models.BooleanField(
        default=False,
        help_text="Explicitly-allowed extra/second payment for the same month",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recorded_fees",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fee_year", "-fee_month", "-payment_date"]
        verbose_name = "Student Fee"
        verbose_name_plural = "Student Fees"
        indexes = [
            models.Index(fields=["student", "fee_year"]),
            models.Index(fields=["fee_month", "fee_year"]),
            models.Index(fields=["payment_date"]),
        ]
        constraints = [
            # Blocks accidental duplicate fee entries per student + month + year.
            models.UniqueConstraint(
                fields=["student", "fee_month", "fee_year"],
                condition=models.Q(is_extra=False),
                name="unique_student_fee_month",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="fee_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.get_fee_month_display()} {self.fee_year} (Rs {self.amount})"

