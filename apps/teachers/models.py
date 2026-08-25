from decimal import Decimal

import django

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.classrooms.models import SchoolClass
from apps.core.constants import MONTHS
from apps.core.models import Sequence

# Django 6.1 renamed CheckConstraint's ``check`` kwarg to ``condition``.
# Detect the installed version so the model works on both old and new Django.
_CHECK_KWARG = "condition" if django.VERSION >= (6, 1) else "check"


class Teacher(models.Model):
    """A teacher employed at the school.

    ``teacher_id`` is generated automatically (e.g. ``TCH-000001``) and is unique
    and permanent. Teachers can be assigned to one or more classes.
    """

    teacher_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    cnic = models.CharField(max_length=20, blank=True, verbose_name="CNIC (optional)")
    phone = models.CharField(max_length=20, verbose_name="Phone Number")
    address = models.TextField(blank=True)
    cnic_front_pic = models.ImageField(
        upload_to="teachers/cnic/", blank=True, null=True, verbose_name="CNIC Front Picture (optional)"
    )
    cnic_back_pic = models.ImageField(
        upload_to="teachers/cnic/", blank=True, null=True, verbose_name="CNIC Back Picture (optional)"
    )
    picture = models.ImageField(
        upload_to="teachers/photos/", blank=True, null=True, verbose_name="Teacher Picture (optional)"
    )
    monthly_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Monthly Salary",
    )
    assigned_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="class_teachers",
        verbose_name="Assigned Class",
        help_text="Primary class assigned to this teacher",
    )
    assigned_classes = models.ManyToManyField(
        SchoolClass, blank=True, related_name="assigned_teachers"
    )
    date_joined = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Soft-delete flag: inactive teachers are hidden from lists but their "
        "salary/attendance history is preserved for financial reports.",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teacher_profile",
        help_text="Linked login account (created in ID Management)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["teacher_id"]
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"

    def __str__(self):
        return f"{self.name} ({self.teacher_id})"

    def save(self, *args, **kwargs):
        if not self.teacher_id:
            self.teacher_id = f"TCH-{Sequence.take_next('teacher'):06d}"
        super().save(*args, **kwargs)

    @property
    def yearly_salary(self) -> Decimal:
        """Yearly salary = monthly salary x 12 (automatic)."""
        return self.monthly_salary * 12


class SalaryStatus(models.TextChoices):
    PAID = "PAID", "Paid"
    PENDING = "PENDING", "Pending"


class TeacherSalary(models.Model):
    """A salary payment made to a teacher (counts as an expense).

    Each teacher may be paid once per month/year. Records are never hard-deleted
    when computing balances so the financial history stays intact.
    """

    teacher = models.ForeignKey(
        Teacher, on_delete=models.PROTECT, related_name="salaries"
    )
    salary_month = models.PositiveSmallIntegerField(choices=MONTHS, verbose_name="Salary Month")
    salary_year = models.PositiveSmallIntegerField(verbose_name="Salary Year")
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_date = models.DateField()
    status = models.CharField(
        max_length=10, choices=SalaryStatus.choices, default=SalaryStatus.PAID
    )
    reference = models.CharField(
        max_length=50, blank=True, help_text="Payment reference if required"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recorded_salaries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-salary_year", "-salary_month", "-payment_date"]
        verbose_name = "Teacher Salary"
        verbose_name_plural = "Teacher Salaries"
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "salary_month", "salary_year"],
                name="unique_teacher_salary_month",
            ),
            models.CheckConstraint(
                **{_CHECK_KWARG: models.Q(amount__gt=0)},
                name="salary_amount_positive"
            ),
        ]

    def __str__(self):
        return f"{self.teacher} - {self.get_salary_month_display()} {self.salary_year}"


class TeacherAttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"
    LEAVE = "LEAVE", "Leave"


class TeacherAttendance(models.Model):
    """A daily self check-in record for one teacher on one date.

    Created automatically when a teacher scans the dynamic QR code displayed
    on the admin dashboard (`POST /api/v1/teacher/attendance/scan/`). One
    record per teacher per date is enforced at the database level; a repeat
    scan is idempotent and simply reports the original check-in time.
    """

    class Source(models.TextChoices):
        QR_SCAN = "QR", "QR Scan"
        MANUAL = "MANUAL", "Manual Entry"
        AUTO = "AUTO", "Auto-System"

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="qr_attendance_records",
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=TeacherAttendanceStatus.choices,
        default=TeacherAttendanceStatus.PRESENT,
    )
    time_in = models.TimeField(null=True, blank=True)
    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.QR_SCAN,
        help_text="How this attendance entry was recorded",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_teacher_attendance",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "teacher__teacher_id"]
        verbose_name = "Teacher Attendance"
        verbose_name_plural = "Teacher Attendance Records"
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "date"],
                name="unique_teacher_attendance_date",
            ),
        ]

    def __str__(self):
        return f"{self.teacher} - {self.date} - {self.get_status_display()}"

