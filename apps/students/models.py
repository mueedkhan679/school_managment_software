from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.classrooms.models import SchoolClass
from apps.core.models import Sequence


class Gender(models.TextChoices):
    MALE = "M", "Male"
    FEMALE = "F", "Female"


class StudentStatus(models.TextChoices):
    NEW_ADMISSION = "NEW_ADMISSION", "New Admission"
    REGULAR = "REGULAR", "Regular"
    PROMOTED = "PROMOTED", "Promoted"


class Student(models.Model):
    """A student enrolled in the school.

    ``student_id`` is generated automatically (e.g. ``STU-000001``) and is unique
    and permanent - deleting a record never re-uses a previously issued ID.
    """

    student_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=StudentStatus.choices,
        default=StudentStatus.NEW_ADMISSION,
        help_text="Visual tag to distinguish student progression."
    )
    roll_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Roll Number",
        help_text="Roll number unique within the class (optional)",
    )
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
    admission_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=(
            "Optional one-time admission fee collected at registration. "
            "Tracked separately from monthly tuition and reported on the dashboard."
        ),
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


class StudentAcademicHistory(models.Model):
    """Archived record of a student's past academic sessions and fee completion status."""
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="academic_history"
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="archived_students",
        help_text="The class the student completed."
    )
    session_year = models.CharField(max_length=20, help_text="e.g. 2025-2026")
    fee_clearance_status = models.CharField(max_length=50, help_text="e.g. '12/12 Paid'")
    status_tag = models.CharField(max_length=20, choices=StudentStatus.choices)
    promoted_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-promoted_date"]
        verbose_name = "Academic History"
        verbose_name_plural = "Academic Histories"

    def __str__(self):
        class_name = self.school_class.name if self.school_class else "Unknown Class"
        return f"{self.student.name} - {class_name} ({self.session_year})"
