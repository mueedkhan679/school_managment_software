from django.db import IntegrityError, transaction

from .models import Teacher


def get_teacher_profile_for_user(user):
    """Return and, when unambiguous, repair the active profile for ``user``."""
    try:
        teacher = user.teacher_profile
    except (AttributeError, Teacher.DoesNotExist):
        teacher = None

    if teacher is not None:
        return teacher if teacher.is_active else None

    username = (getattr(user, "username", "") or "").strip()
    full_name = (getattr(user, "get_full_name", lambda: "")() or "").strip()
    if not username and not full_name:
        return None

    candidates = Teacher.objects.filter(is_active=True, user__isnull=True)
    matches = candidates.filter(teacher_id__iexact=username)
    if not matches.exists():
        matches = candidates.filter(name__iexact=username)
    if not matches.exists() and full_name:
        matches = candidates.filter(name__iexact=full_name)

    if matches.count() != 1:
        return None
    teacher = matches.first()

    try:
        with transaction.atomic():
            teacher.user = user
            teacher.save(update_fields=["user"])
    except IntegrityError:
        # Another request may have linked this profile concurrently. Reload
        # the relation and only return it when it belongs to this user.
        teacher = Teacher.objects.filter(pk=teacher.pk, user=user).first()
    return teacher if teacher is not None and teacher.is_active else None