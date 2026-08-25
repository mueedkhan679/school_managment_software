# -*- coding: utf-8 -*-
"""Reusable auto-absent logic used by the ``mark_auto_absent`` command and the
Teacher Attendance Register view (which triggers it after the closing gate).
"""

from datetime import time

from django.utils import timezone

from apps.teachers.models import (
    Teacher,
    TeacherAttendance,
    TeacherAttendanceStatus,
)

# School closing time — after this, a missing check-in counts as Absent.
CUTOFF_HOUR = 14  # 02:00 PM
CUTOFF_MINUTE = 0


def cutoff_passed(target_date=None, now=None) -> bool:
    """True when the closing time has passed for ``target_date``."""
    now = now or timezone.localtime()
    target_date = target_date or now.date()
    if target_date < now.date():
        return True  # past days are always closed
    if target_date == now.date():
        return now.time() >= time(CUTOFF_HOUR, CUTOFF_MINUTE)
    return False  # future dates are never closed


def mark_auto_absent(target_date=None, force=False) -> int:
    """Bulk-mark active teachers with no Present/Leave entry as Absent.

    Returns the number of teacher records created (0 if none needed or the
    cutoff has not yet passed and ``force`` is False).
    """
    now = timezone.localtime()
    target_date = target_date or now.date()

    if not force and not cutoff_passed(target_date, now):
        return 0

    todays_entries = set(
        TeacherAttendance.objects.filter(date=target_date).values_list(
            "teacher_id", flat=True
        )
    )
    missing_ids = list(
        Teacher.objects.filter(is_active=True)
        .exclude(id__in=todays_entries)
        .values_list("id", flat=True)
    )

    if not missing_ids:
        return 0

    now_time = now.time()
    TeacherAttendance.objects.bulk_create(
        [
            TeacherAttendance(
                teacher_id=tid,
                date=target_date,
                status=TeacherAttendanceStatus.ABSENT,
                source="AUTO",
                recorded_by=None,
                time_in=None,
                created_at=now,
                updated_at=now,
            )
            for tid in missing_ids
        ]
    )
    return len(missing_ids)
