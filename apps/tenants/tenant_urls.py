"""Tenant-scoped URL routes.

When the TenantMiddleware identifies a tenant from /t/<slug>/..., it strips the
leading /t/<slug>/ and sets the tenant DB alias.  The remaining path is matched
against the patterns below, so tenant users land on their school's portal without
needing to know the slug.

Patterns here intentionally include the app-level URLconfs so the same views that
serve the "single tenant" experience continue to work inside a tenant context
(they'll be routed to the tenant DB by the TenantRouter).
"""

from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # School landing / default dashboard after login.
    path("", include("apps.core.urls")),
    # Role portals.
    path("teacher-portal/", include("apps.teachers.portal_urls")),
    path("student-portal/", include("apps.students.portal_urls")),
    path(
        "student-portal/api/data/",
        RedirectView.as_view(pattern_name="student_portal_api_data", permanent=False),
        name="tenant_student_portal_api_data",
    ),
    # School-scoped apps (routed to the tenant DB by the TenantRouter).
    path("classrooms/", include("apps.classrooms.urls")),
    path("students/", include("apps.students.urls")),
    path("teachers/", include("apps.teachers.urls")),
    path("fees/", include("apps.fees.urls")),
    path("attendance/", include("apps.attendance.urls")),
    # Accounts login/logout also live inside the tenant so the session is
    # created against the tenant DB.
    path("accounts/", include("apps.accounts.urls")),
]