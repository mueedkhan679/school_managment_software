"""Tenant identification middleware with Kill Switch enforcement.

Request flow:
  1. Skip tenant resolution for bypassed paths (master-admin, admin, static,
     media, favicon).
  2. Resolve the active tenant using, in priority order:
       a. ``HTTP_X_TENANT_KEY`` / ``HTTP_X_TENANT_SLUG`` header
          (API / mobile app / server-to-server calls)
       b. ``?tenant=<slug>`` query param (browser / deep links)
       c. URL path prefix ``/t/<slug>/...`` (browser, default on localhost)
       d. Subdomain ``<slug>.<domain>`` (production, when enabled)
  3. Look up the Tenant in the master DB.
  4. If ``tenant.is_active is False`` → render the Suspended page (Kill Switch).
  5. Dynamically register the tenant DB alias if needed.
  6. Set ``request.tenant`` and the thread-local DB alias for the router.
  7. Strip the path prefix (only for the URL-prefix method) so downstream URL
     patterns continue to match the original patterns.
  8. After the response, clear the thread-local to prevent leaks.

Bypassed paths:
  - ``settings.MASTER_ADMIN_URL_PREFIX`` — Super-Admin portal (no tenant context)
  - ``/admin/`` — Django built-in admin
  - ``/static/`` and ``/media/`` — Static assets
  - ``/favicon.ico``
"""

from __future__ import annotations

import logging
import re
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render

from .db_router import set_current_db_alias
from .models import Tenant
from .utils import ensure_tenant_migrations, register_tenant_db

logger = logging.getLogger("tenants.middleware")

# Paths that bypass tenant resolution entirely.
_BYPASS_PREFIXES = [
    settings.MASTER_ADMIN_URL_PREFIX.rstrip("/") + "/",
    "/admin/",
    "/static/",
    "/media/",
    "/favicon.ico",
]

# Regex to extract tenant slug from URL: /t/<slug>/...
_TENANT_URL_PATTERN = re.compile(r"^/t/(?P<slug>[a-zA-Z0-9_-]+)/")


def _is_bypass(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _BYPASS_PREFIXES)


def _extract_subdomain(request: HttpRequest) -> str | None:
    """Return the lowest-level subdomain of the request host, if any."""
    host = request.get_host()
    if not host:
        return None
    # Strip port.
    host = host.split(":")[0].lower()
    parts = host.split(".")
    if len(parts) < 3:
        return None
    candidate = parts[0]
    # Ignore common localhost aliases.
    if candidate in {"localhost", "127", "0", "www"}:
        return None
    return candidate


class TenantMiddleware:
    """Identify the active tenant from the request and route DB queries accordingly."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Default: no tenant context.
        request.tenant = None
        request.tenant_slug = None

        path = request.path

        if _is_bypass(path):
            set_current_db_alias(None)
            return self.get_response(request)

        # --- Tenant identification (priority order) ---
        tenant_slug: str | None = None
        identification_method: str | None = None

        # 1. HTTP header X-Tenant-Key or X-Tenant-Slug
        #    (API / server-to-server calls — the Flutter mobile app sends
        #    ``X-Tenant-Slug`` on every request so authentication and data
        #    queries are routed to the correct tenant database.)
        header_key = request.META.get("HTTP_X_TENANT_KEY")
        if not header_key:
            header_key = request.META.get("HTTP_X_TENANT_SLUG")
        if header_key:
            tenant_slug = str(header_key).strip().lower()
            identification_method = "header"

        # 2. Query parameter ?tenant=<slug>
        if not tenant_slug:
            qp_slug = request.GET.get("tenant")
            if qp_slug:
                tenant_slug = str(qp_slug).strip().lower()
                identification_method = "query"

        # 3. URL path prefix /t/<slug>/
        if not tenant_slug:
            match = _TENANT_URL_PATTERN.match(path)
            if match:
                tenant_slug = match.group("slug")
                identification_method = "path"

        # 4. Subdomain (production), only when enabled.
        if not tenant_slug and getattr(
            settings, "TENANT_IDENTIFICATION_MODE", "path"
        ).startswith("subdomain"):
            subdomain = _extract_subdomain(request)
            if subdomain:
                tenant_slug = subdomain
                identification_method = "subdomain"

        if tenant_slug:
            try:
                tenant = Tenant.objects.get(slug=tenant_slug)
            except Tenant.DoesNotExist:
                logger.warning(
                    "tenant_lookup_failed slug=%s method=%s path=%s",
                    tenant_slug,
                    identification_method,
                    path,
                )
                return HttpResponseForbidden(
                    "<h1>School Not Found</h1>"
                    "<p>No school registered with identifier '{}'</p>".format(tenant_slug)
                )

            # Kill Switch enforcement.
            if not tenant.is_active:
                logger.info(
                    "tenant_suspended slug=%s method=%s path=%s",
                    tenant_slug,
                    identification_method,
                    path,
                )
                return render(
                    request,
                    "tenants/suspended.html",
                    {
                        "tenant": tenant,
                        "identification_method": identification_method,
                    },
                    status=403,
                )

            # Portal Lock enforcement.
            if tenant.is_locked:
                logger.info(
                    "tenant_locked slug=%s method=%s path=%s",
                    tenant_slug,
                    identification_method,
                    path,
                )
                return render(
                    request,
                    "tenants/locked.html",
                    {
                        "tenant": tenant,
                        "identification_method": identification_method,
                    },
                    status=403,
                )

            # Register the tenant's DB connection if not already done.
            try:
                register_tenant_db(tenant)
                # Self-heal the tenant schema on the fly: if any expected table
                # (e.g. teachers_teachersalary) is missing — even when Django's
                # migration history claims it was applied — run / fake-apply the
                # missing migrations automatically so the user never has to run
                # manual SQL deletes or management commands again.
                if getattr(settings, "TENANT_AUTO_REPAIR_ENABLED", True):
                    ensure_tenant_migrations(tenant)
            except Exception:  # noqa: S110
                logger.exception(
                    "failed_to_load_or_repair_tenant_db slug=%s", tenant_slug
                )
                return HttpResponseForbidden(
                    "<h1>Service Unavailable</h1>"
                    "<p>This school's database could not be verified. Please try again later.</p>"
                )

            # Set tenant context.
            request.tenant = tenant
            request.tenant_slug = tenant_slug
            set_current_db_alias(tenant.db_alias)

            # For the URL-prefix method, strip /t/<slug>/ so downstream URL
            # resolution continues to match the original URL patterns.
            if identification_method == "path":
                request.path_info = _TENANT_URL_PATTERN.sub("/", path)
                # Also normalise PATH_INFO for any code that reads it.
                if hasattr(request, "META"):
                    request.META["PATH_INFO"] = request.path_info
        else:
            # No tenant identified — operate on default (master) DB.
            set_current_db_alias(None)

        try:
            response = self.get_response(request)
        finally:
            # Always clear the thread-local so the next request starts clean.
            set_current_db_alias(None)

        return self._fix_redirect(request, response)

    @staticmethod
    def _fix_redirect(request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Adjust redirect Location headers to stay inside the tenant URL space.

        Any relative redirect issued while a tenant is active is re-prefixed with
        ``/t/<slug>/`` so the browser remains inside the tenant's URL scope and
        the next request continues to route to the tenant's database.
        """
        from .utils import with_tenant_prefix

        if response.status_code not in (301, 302):
            return response
        if getattr(request, "tenant", None) is None:
            return response

        location = response.get("Location", "")
        if not location:
            return response
        # Don't touch absolute URLs (external redirects, OAuth, etc.).
        if location.startswith(("http://", "https://", "//")):
            return response

        new_location = with_tenant_prefix(location, request)
        if new_location != location:
            response["Location"] = new_location
        return response
