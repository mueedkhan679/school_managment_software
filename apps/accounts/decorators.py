"""Role-based access-control decorators.

These decorators protect views from direct URL access:
- Anonymous users are redirected to the login page with a ``next`` query
  parameter so they return where they intended to go after logging in.
- Authenticated users without the required role get a 403 Forbidden.
"""
from functools import wraps
from urllib.parse import quote

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from apps.tenants.utils import with_tenant_prefix

from .models import Role


def role_required(*roles):
    """Allow a view only to authenticated users whose role is in ``roles``.

    Unauthenticated users are redirected to the login page.  When the request
    is inside a tenant context (``request.tenant`` is set) the login URL is
    prefixed with ``/t/<slug>/`` so the browser lands on the tenant-scoped
    login form instead of the global ``/accounts/login/`` (which would make
    the TenantMiddleware fail with "No school registered with identifier
    'accounts'").
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = with_tenant_prefix(reverse("accounts:login"), request)
                path = quote(request.get_full_path())
                return redirect(f"{login_url}?{REDIRECT_FIELD_NAME}={path}")
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


# Admin-only access decorator used across the main management system.
admin_required = role_required(Role.ADMIN)
teacher_required = role_required(Role.TEACHER)
student_required = role_required(Role.STUDENT)

