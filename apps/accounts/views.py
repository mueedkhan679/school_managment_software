from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .decorators import admin_required
from .forms import ChangeCredentialsForm, LoginForm

User = get_user_model()

from apps.core.forms import SchoolSettingsForm  # noqa: E402  (model imports below)
from apps.core.models import SchoolSettings  # noqa: E402

from django.core.cache import cache

ERROR_INVALID_CREDENTIALS = "Invalid username or password."
ERROR_DISABLED_ACCOUNT = "Your account is disabled. Please contact the administrator."
ERROR_NOT_ADMIN = "Access denied: this account is not an administrator."
ERROR_TOO_MANY_ATTEMPTS = "Too many failed login attempts. Please try again in 5 minutes."
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 300
REMEMBER_ME_SECONDS = 14 * 24 * 60 * 60  # "Remember me" keeps the session 2 weeks


def _get_client_ip(request):
    """Retrieve the client IP address from request headers."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def _safe_next_url(request, next_url):
    """Return ``next_url`` only if it is a safe internal redirect target."""
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return None


def _redirect_for_role(user):
    """Return the default home landing page URL based on user role."""
    if user.is_teacher:
        return reverse("teacher_portal:dashboard")
    elif user.is_student:
        return reverse("student_portal:dashboard")
    return reverse("core:dashboard")


def admin_login(request):
    """Universal login view (GET renders form, POST authenticates).

    - Verifies credentials via Django auth (hashed-password comparison).
    - Rate-limiting protection: Locks out after 5 consecutive failed attempts.
    - Distinguishes invalid credentials from disabled accounts.
    - Dynamically redirects based on user role:
      * ADMIN -> Main Dashboard
      * TEACHER -> Teacher Portal
      * STUDENT -> Student Portal
    - Rotates the session key on login (anti-fixation).
    - Honors a validated ``next`` parameter; open redirects are blocked.
    """
    if request.user.is_authenticated:
        return redirect(_redirect_for_role(request.user))

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"].strip()
        password = form.cleaned_data["password"]
        ip = _get_client_ip(request)

        ip_key = f"login_attempts_ip_{ip}"
        user_key = f"login_attempts_user_{username.lower()}"

        ip_attempts = cache.get(ip_key, 0)
        user_attempts = cache.get(user_key, 0)

        if ip_attempts >= MAX_FAILED_ATTEMPTS or user_attempts >= MAX_FAILED_ATTEMPTS:
            form.add_error(None, ERROR_TOO_MANY_ATTEMPTS)
        else:
            user = authenticate(request, username=username, password=password)

            if user is None:
                cache.set(ip_key, ip_attempts + 1, LOCKOUT_DURATION_SECONDS)
                cache.set(user_key, user_attempts + 1, LOCKOUT_DURATION_SECONDS)
                # Distinguish a disabled account from a simple bad login.
                try:
                    existing = User.objects.get(username=username)
                except User.DoesNotExist:
                    existing = None
                if existing is not None and not existing.is_active:
                    form.add_error(None, ERROR_DISABLED_ACCOUNT)
                else:
                    form.add_error(None, ERROR_INVALID_CREDENTIALS)
            else:
                cache.delete(ip_key)
                cache.delete(user_key)
                login(request, user)  # cycles the session key (anti-fixation)

                # "Remember me": keep the session alive for two weeks,
                # otherwise expire it as soon as the browser closes.
                if request.POST.get("remember_me"):
                    request.session.set_expiry(REMEMBER_ME_SECONDS)
                else:
                    request.session.set_expiry(0)

                safe_next = _safe_next_url(request, next_url)
                return redirect(safe_next or _redirect_for_role(user))

    return render(
        request,
        "accounts/login.html",
        {"form": form, "next": next_url},
    )


@require_POST
def admin_logout(request):
    """Securely log out: POST-only (prevents CSRF-based logout attacks).

    ``logout()`` flushes the session data and rotates the key.
    """
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("accounts:login")


@admin_required
def change_credentials(request):
    """Let the logged-in admin change their username/password and school settings.

    The page hosts two independent forms: the credentials form and the School
    Settings form (name / phone / logo). Each submit button is named so we can
    detect which form was posted; the other one stays unbound.
    """
    creds_form = ChangeCredentialsForm(user=request.user)
    settings_form = SchoolSettingsForm(instance=SchoolSettings.load())

    if request.method == "POST":
        if "save_settings" in request.POST:
            # --- School Settings form (multipart: may include logo upload) ---
            settings_form = SchoolSettingsForm(
                request.POST, request.FILES, instance=SchoolSettings.load()
            )
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "School settings saved successfully.")
                return redirect("accounts:change_credentials")
        else:
            # --- Credentials form ---
            creds_form = ChangeCredentialsForm(user=request.user, data=request.POST)
            if creds_form.is_valid():
                creds_form.save()
                # Keep the current session valid after a password change.
                from django.contrib.auth import update_session_auth_hash

                update_session_auth_hash(request, request.user)
                messages.success(request, "Your credentials were updated successfully.")
                return redirect("core:dashboard")

    return render(
        request,
        "accounts/change_credentials.html",
        {"form": creds_form, "settings_form": settings_form},
    )

