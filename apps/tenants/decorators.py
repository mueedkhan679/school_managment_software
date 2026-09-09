"""Access-control decorators for the master admin portal."""

from functools import wraps
from urllib.parse import quote

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


def superadmin_required(view_func):
    """Allow access only to authenticated users with the SUPERADMIN role.

    Checks are performed against the default (master) database.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse("accounts:login")
            path = quote(request.get_full_path())
            return redirect(f"{login_url}?{REDIRECT_FIELD_NAME}={path}")
        if not getattr(request.user, "is_superadmin", False):
            raise PermissionDenied("Super-Admin access required.")
        return view_func(request, *args, **kwargs)

    return _wrapped
