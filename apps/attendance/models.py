from django.conf import settings
from django.db import models

from apps.students.models import Student


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"
    LEAVE = "LEAVE", "Leave"


class Attendance(models.Model):
    """A single attendance record for one student on one date.

    Each student may have exactly one record per date (unique constraint), so
    duplicate marking for the same student/date is impossible unless an existing
    record is edited.
    """

    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="attendance_records"
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT
    )
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_attendance",
        help_text="Teacher who marked this attendance",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "student__student_id"]
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"], name="unique_student_attendance_date"
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.date} - {self.get_status_display()}"

    @property
    def school_class(self):
        """Convenience accessor for the student's class."""
        return self.student.school_class

    @property
    def marked_by_teacher(self):
        """The Teacher profile tied to the user who recorded this attendance.

        Returns None when the record was created by an admin/system without a
        linked teacher profile (e.g. auto-absent runs or non-teacher users).
        """
        user = self.marked_by
        if user is None:
            return None
        try:
            teacher = getattr(user, "teacher_profile", None)
        except Exception:
            return None
        if teacher is None or not teacher.is_active:
            return None
        return teacher


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Attendance)
def attendance_post_save(sender, instance, created, **kwargs):
    """Auto-generate an in-app notification and an FCM push notification
    whenever an attendance record is created or updated.
    """
    if not instance.student.user:
        return

    # Don't trigger for bulk updates if they bypass save(), but update_or_create calls save().
    marker_name = "Admin"
    if instance.marked_by:
        marker_name = instance.marked_by.get_full_name() or instance.marked_by.username
        if instance.marked_by_teacher:
            marker_name = instance.marked_by_teacher.name

    status_str = str(instance.status).upper()
    date_str = instance.date.strftime('%Y-%m-%d')
    title = f"Attendance Marked: {status_str}"
    message = f"Your attendance for {date_str} has been marked as {status_str} by {marker_name}."

    try:
        from apps.core.models import Notification
        from apps.core.fcm import send_fcm_notification

        # Create in-app notification
        Notification.objects.create(
            user=instance.student.user,
            title=title,
            message=message,
        )

        # Send push notification
        send_fcm_notification(instance.student.user, title, message)
    except Exception:
        # Never break the save transaction for notification issues
        pass


