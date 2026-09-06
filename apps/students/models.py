from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from apps.classrooms.models import SchoolClass
from apps.core.models import Sequence

#: Number of monthly fee instalments in one academic session.
MONTHS_PER_SESSION = 12


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

    # ------------------------------------------------------------------
    # Academic session & fee-clearance tracker
    # ------------------------------------------------------------------
    @property
    def current_session(self) -> str:
        """Academic session of the student's CURRENT class.

        Derived from the most recent fee paid in the current class (e.g.
        '2025-2026'); falls back to the calendar-year session when no fee
        exists yet.
        """
        latest = (
            self.fees.filter(school_class=self.school_class)
            .order_by("-fee_year", "-payment_date", "-id")
            .first()
        )
        if latest and latest.session_year:
            return latest.session_year
        now_year = timezone.now().year
        return f"{now_year}-{now_year + 1}"

    def paid_months_count_for(self, school_class, session_year) -> int:
        """Number of distinct PAID **standard** monthly instalments for a
        class + session.

        Counting rule (deliberately resilient to the ways fee rows drift):
          * only ``status=PAID``, non-``is_extra`` records count — extra /
            late / exam receipts never advance the 12-month tracker;
          * a fee counts when its stored ``session_year`` equals the given
            ``session_year`` (the current active session), **or** its label is
            blank (legacy rows created before the session-aware migration /
            records where the session wasn't auto-derived).
        This guarantees 12 genuinely-paid standard months for the current
        class are never under-counted because of a missing or lightly
        inconsistent session label, while a mismatch on a *different* session
        still excludes the row so sessions can't be double-counted.
        """
        from django.db.models import Q

        from apps.fees.models import FeeStatus

        return (
            self.fees.filter(
                school_class=school_class,
                status=FeeStatus.PAID,
                is_extra=False,
            )
            .filter(Q(session_year=session_year) | Q(session_year=""))
            .values("fee_month")
            .distinct()
            .count()
        )

    @property
    def paid_months_count(self) -> int:
        """Distinct paid months in the current class for the current session."""
        return self.paid_months_count_for(self.school_class, self.current_session)

    @property
    def is_fee_cleared(self) -> bool:
        """True once all 12 monthly instalments of the current session are paid.

        When True, the active fee tracker is locked (no further standard
        monthly fee collection for this class/session) and the student is
        ready to be promoted.
        """
        return self.paid_months_count >= MONTHS_PER_SESSION

    @property
    def has_cleared_fees(self) -> bool:
        """Alias for ``is_fee_cleared`` used by the admin change page and
        templates to decide whether the active Promote button renders."""
        return self.is_fee_cleared

    @property
    def fee_clearance_status(self) -> str:
        """Human label, e.g. '12/12 Months Cleared' or '9/12 Months Paid'."""
        if self.is_fee_cleared:
            return f"{MONTHS_PER_SESSION}/{MONTHS_PER_SESSION} Months Cleared"
        return f"{self.paid_months_count}/{MONTHS_PER_SESSION} Months Paid"

    def is_session_cleared(self, school_class, session_year) -> bool:
        """True when all 12 monthly instalments are paid for class+session."""
        return self.paid_months_count_for(school_class, session_year) >= MONTHS_PER_SESSION

    @transaction.atomic
    def promote_to(self, new_class, force=False):
        """Archive the finished academic session and advance the student.

        * Saves the previous class, session year and fee-clearance status into
          ``StudentAcademicHistory`` (permanent record, never lost).
        * Moves the student into ``new_class`` and flips the status badge to
          PROMOTED. Because the active fee tracker is derived per class, it
          naturally resets to 0/12 for the new academic session.
        * ``force=True`` bypasses the 12-month clearance requirement (used by
          the bulk-action override).

        Returns the created ``StudentAcademicHistory`` row.
        """
        if not self.is_fee_cleared and not force:
            raise ValidationError(
                f"{self.name} ({self.student_id}) has not completed "
                f"{MONTHS_PER_SESSION}/{MONTHS_PER_SESSION} months of fees for "
                f"{self.school_class.name} (Session {self.current_session}). "
                "Promotion is not allowed until the session is fee-cleared."
            )
        if new_class.pk == self.school_class_id:
            raise ValidationError(
                f"{self.name} is already enrolled in {new_class.name}."
            )

        archived = StudentAcademicHistory.objects.create(
            student=self,
            school_class=self.school_class,
            session_year=self.current_session,
            fee_clearance_status=self.fee_clearance_status,
            status_tag=StudentStatus.PROMOTED,
        )
        self.school_class = new_class
        self.status = StudentStatus.PROMOTED
        # Fee tracker is class-scoped, so it automatically resets to 0/12 in
        # the new class — a fresh academic cycle begins.
        self.save(update_fields=["school_class", "status", "updated_at"])
        return archived


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
