"""Custom authentication backend for multi-tenant user lookup.

The default ``ModelBackend`` always queries the *default* database, which means
tenant users (who live only in their tenant's SQLite file) can never be loaded
on subsequent requests.  This backend reads the tenant DB alias from the
thread-local set by ``TenantMiddleware`` and queries the correct database.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .db_router import get_current_db_alias

User = get_user_model()


class TenantBackend(ModelBackend):
    """Authenticate and fetch users against the active tenant's database."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        """Only handle requests that have a tenant context."""
        if request is None or getattr(request, "tenant", None) is None:
            return None
        alias = request.tenant.db_alias
        try:
            user = User.objects.using(alias).get(username=username)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        """Fetch the user from the tenant DB identified by the thread-local alias.

        Falls back to the default database when no tenant context is active
        (e.g. superadmin / master-admin sessions that were established before
        ``AUTHENTICATION_BACKENDS`` was reconfigured, or via ``force_login()``
        without an explicit backend).
        """
        alias = get_current_db_alias()
        if alias is not None:
            try:
                return User.objects.using(alias).get(pk=user_id)
            except User.DoesNotExist:
                return None
        # No tenant context — fall back to the default DB.
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
