"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.api.views import StudentProfileView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Master Admin Super-Admin portal — bypasses tenant middleware entirely.
    path('master-admin/', include('apps.tenants.urls')),
    # Standalone app includes — registered BEFORE the tenant include so that
    # ``reverse()`` resolves app names to their non-tenant paths (e.g.
    # ``/accounts/login/`` not ``/t/accounts/login/``).  The ``with_tenant_prefix``
    # helper in ``apps.tenants.utils`` then re-prefixes with ``/t/<slug>/`` when
    # redirecting inside a tenant context.
    path('accounts/', include('apps.accounts.urls')),
    path('classrooms/', include('apps.classrooms.urls')),
    path('students/', include('apps.students.urls')),
    path('teachers/', include('apps.teachers.urls')),
    path('fees/', include('apps.fees.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('teacher-portal/', include('apps.teachers.portal_urls')),
    path('student-portal/', include('apps.students.portal_urls')),
    # Mobile API: student portal data endpoint for the Flutter app
    path('student-portal/api/data/', StudentProfileView.as_view(), name='student_portal_api_data'),
    path('api/v1/', include('apps.api.urls')),
    # Tenant-scoped school routes — placed AFTER all standalone app includes so
    # that ``reverse()`` resolves to non-tenant paths.  The TenantMiddleware
    # strips the leading ``/t/<slug>/`` prefix, so these patterns are matched
    # against the remaining path (e.g. ``/`` or ``/dashboard/``).
    path('t/', include('apps.tenants.tenant_urls')),
    # Catch-all: core routes (index, dashboard) — must be last.
    path('', include('apps.core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
