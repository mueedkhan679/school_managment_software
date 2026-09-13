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

import logging

logger = logging.getLogger("accounts.decorators")


def role_required(*roles):
    """Allow a view only to authenticated users whose role is in ``roles``.

    Unauthenticated users are redirected to the login page.  When the request
    is inside a tenant context (``request.tenant`` is set) the login URL is
    prefixed with ``/t/<slug>/`` so the browser lands on the tenant-scoped
    login form instead of the global ``/accounts/login/`` (which would make
    the TenantMiddleware fail with "No school registered with identifier
    'accounts'").

    Authenticated users without the required role raise ``PermissionDenied``
    (403).  The denial is always logged — together with the user's effective
    role — so missing/incorrectly provisioned ``UserProfile`` records or DB
    routing problems are diagnosable instead of surfacing as a mysterious
    403 page.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = with_tenant_prefix(reverse("accounts:login"), request)
                path = quote(request.get_full_path())
                return redirect(f"{login_url}?{REDIRECT_FIELD_NAME}={path}")
            # Defensive role read: a user record without a ``role`` column
            # (e.g. loaded from the wrong database) must be logged, not
            # silently converted into a generic 403.
            user_role = getattr(request.user, "role", None)
            if user_role not in roles:
                logger.warning(
                    "role_required_denied path=%s user=%s effective_role=%s "
                    "required_roles=%s tenant=%s",
                    request.path,
                    getattr(request.user, "username", "?"),
                    user_role,
                    list(roles),
                    getattr(request, "tenant_slug", None),
                )
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


# Admin-only access decorator used across the main management system.
admin_required = role_required(Role.ADMIN)
teacher_required = role_required(Role.TEACHER)
student_required = role_required(Role.STUDENT)

