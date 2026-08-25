"""Global template context processors for the School Management System."""
from .models import SchoolSettings


def school_info(request):
    """Expose dynamic school branding to every Django template.

    Provides ``school_name``, ``school_phone`` and ``school_logo`` from the
    singleton :class:`~apps.core.models.SchoolSettings` record so templates no
    longer rely on hardcoded branding strings.
    """
    settings_obj = SchoolSettings.load()
    return {
        "school_name": settings_obj.school_name or SchoolSettings.DEFAULT_SCHOOL_NAME,
        "school_phone": settings_obj.school_phone,
        "school_logo": settings_obj.school_logo,
    }
