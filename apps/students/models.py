from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.classrooms.models import SchoolClass
from apps.core.models import Sequence


class Gender(models.TextChoices):
    MALE = "M", "Male"
    FEMALE = "F", "Female"


class Student(models.Model):
    """A student enrolled in the school.

    ``student_id`` is generated automatically (e.g. ``STU-000001``) and is unique
    and permanent - deleting a record never re-uses a previously issued ID.
    """

    student_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="students"
    )
    date_of_birth = models.DateField()
    form_b_number = models.CharField(
        max_length=50, blank=True, verbose_name="Form/B-Form Number"
    )
    gender = models.CharField(max_length=1, choices=Gender.choices)
    email = models.EmailField(blank=True, verbose_name="Gmail (optional)")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Phone (optional)")
    address = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to="students/photos/",
        blank=True,
        null=True,
        verbose_name="Passport size picture (optional)",
    )
    custom_monthly_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Optional per-student override of the class monthly fee",
    )
    admission_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Soft-delete flag: inactive students are hidden from lists but their "
        "fee/attendance history is preserved for financial reports.",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profile",
        help_text="Linked login account (created in ID Management)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["student_id"]
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        return f"{self.name} ({self.student_id})"

    def save(self, *args, **kwargs):
        if not self.student_id:
            self.student_id = f"STU-{Sequence.take_next('student'):06d}"
        super().save(*args, **kwargs)

    @property
    def effective_monthly_fee(self) -> Decimal:
        """The monthly fee actually charged to this student."""
        if self.custom_monthly_fee is not None:
            return self.custom_monthly_fee
        return self.school_class.monthly_fee

    @property
    def yearly_fee(self) -> Decimal:
        """Yearly expected fee = effective monthly fee x 12 (automatic)."""
        return self.effective_monthly_fee * 12

