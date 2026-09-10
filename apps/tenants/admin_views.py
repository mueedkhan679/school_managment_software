"""Master Admin Portal views for Super-Admin school management."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
import logging

logger = logging.getLogger("tenants.admin_views")
from django.views.decorators.http import require_POST

from apps.accounts.models import Role

from .decorators import superadmin_required
from .models import Tenant
from .utils import (
    delete_tenant_db,
    ensure_tenant_admin,
    provision_tenant_db,
    register_tenant_db,
)

User = get_user_model()


@superadmin_required
def master_dashboard(request):
    """Super-Admin dashboard listing all tenant schools."""
    tenants = Tenant.objects.all()
    query = request.GET.get("q", "").strip()
    if query:
        tenants = tenants.filter(
            Q(school_name__icontains=query) | Q(slug__icontains=query)
        )

    context = {
        "tenants": tenants,
        "query": query,
        "total_count": Tenant.objects.count(),
        "active_count": Tenant.objects.filter(is_active=True).count(),
        "suspended_count": Tenant.objects.filter(is_active=False).count(),
        "locked_count": Tenant.objects.filter(is_locked=True).count(),
    }
    return render(request, "tenants/master_dashboard.html", context)


@superadmin_required
def school_add(request):
    """Create a new tenant school and provision its database.

    The Master Admin may optionally supply custom admin credentials
    (username + password) for the initial superuser account that gets
    seeded inside the new tenant's database.  When omitted, sensible
    defaults are used by :func:`provision_tenant_db`.
    """
    if request.method == "POST":
        school_name = request.POST.get("school_name", "").strip()
        slug = request.POST.get("slug", "").strip().lower().replace(" ", "-")
        admin_email = request.POST.get("admin_email", "").strip()
        admin_phone = request.POST.get("admin_phone", "").strip()
        max_students = request.POST.get("max_students", "500").strip()
        admin_username = request.POST.get("admin_username", "").strip()
        admin_password = request.POST.get("admin_password", "").strip()

        if not school_name or not slug:
            messages.error(request, "School name and slug are required.")
            return render(request, "tenants/school_form.html", {
                "title": "Add New School",
                "action_text": "Create School & Provision Database",
            })

        if Tenant.objects.filter(slug=slug).exists():
            messages.error(request, f"A school with slug '{slug}' already exists.")
            return render(request, "tenants/school_form.html", {
                "title": "Add New School",
                "action_text": "Create School & Provision Database",
            })

        # Validate custom admin credentials when provided.
        if admin_username and not admin_password:
            messages.error(
                request, "If you provide a custom admin username, a password is required."
            )
            return render(request, "tenants/school_form.html", {
                "title": "Add New School",
                "action_text": "Create School & Provision Database",
            })
        if admin_username and len(admin_password) < 8:
            messages.error(
                request, "The custom admin password must be at least 8 characters long."
            )
            return render(request, "tenants/school_form.html", {
                "title": "Add New School",
                "action_text": "Create School & Provision Database",
            })

        tenant = Tenant.objects.create(
            school_name=school_name,
            slug=slug,
            admin_email=admin_email,
            admin_phone=admin_phone,
            max_students=int(max_students) if max_students.isdigit() else 500,
        )

        # Provision the tenant database (create DB, run migrations, seed admin user)
        admin_username = provision_tenant_db(
            tenant,
            admin_username=admin_username or None,
            admin_password=admin_password or None,
        )

        messages.success(
            request,
            f"School '{tenant.school_name}' created successfully! "
            f"Database provisioned. Admin account username: {admin_username}"
        )
        return redirect("tenants:master_dashboard")

    context = {
        "title": "Add New School",
        "action_text": "Create School & Provision Database",
    }
    return render(request, "tenants/school_form.html", context)


@superadmin_required
def school_edit(request, slug):
    """Edit a tenant school's details."""
    tenant = get_object_or_404(Tenant, slug=slug)

    if request.method == "POST":
        tenant.school_name = request.POST.get("school_name", tenant.school_name).strip()
        tenant.admin_email = request.POST.get("admin_email", "").strip()
        tenant.admin_phone = request.POST.get("admin_phone", "").strip()
        max_students = request.POST.get("max_students", "500").strip()
        tenant.max_students = int(max_students) if max_students.isdigit() else tenant.max_students
        tenant.save()
        messages.success(request, f"School '{tenant.school_name}' updated.")
        return redirect("tenants:master_dashboard")

    context = {
        "title": f"Edit School: {tenant.school_name}",
        "action_text": "Save Changes",
        "tenant": tenant,
    }
    return render(request, "tenants/school_form.html", context)


@superadmin_required
@require_POST
def school_toggle(request, slug):
    """Toggle a school's Kill Switch (is_active)."""
    tenant = get_object_or_404(Tenant, slug=slug)
    tenant.is_active = not tenant.is_active
    tenant.save(update_fields=["is_active", "updated_at"])

    status_text = "activated" if tenant.is_active else "suspended"
    messages.success(request, f"School '{tenant.school_name}' has been {status_text}.")
    return redirect("tenants:master_dashboard")


@superadmin_required
@require_POST
def school_lock(request, slug):
    """Toggle a school's portal Lock (is_locked).

    When locked the TenantMiddleware intercepts every request for that
    tenant and displays the portal-blocked message.  Only the Master Admin
    (whose requests bypass the tenant middleware) can unlock the portal.
    """
    tenant = get_object_or_404(Tenant, slug=slug)
    tenant.is_locked = not tenant.is_locked
    tenant.save(update_fields=["is_locked", "updated_at"])

    if tenant.is_locked:
        messages.success(
            request, f"Portal for '{tenant.school_name}' has been locked."
        )
    else:
        messages.success(
            request, f"Portal for '{tenant.school_name}' has been unlocked."
        )
    return redirect("tenants:master_dashboard")


@superadmin_required
def school_reset_password(request, slug):
    """Forcibly reset (or create) a school admin's password.

    Guarantees an ADMIN-role user exists inside the tenant database before the
    form is rendered or a password change is applied, so tenant login can never
    fail with a 403 Access Denied caused by a missing local user/role record.
    """
    tenant = get_object_or_404(Tenant, slug=slug)

    # Ensure the tenant DB is registered.
    try:
        register_tenant_db(tenant)
    except Exception as e:
        logger.exception(f"Failed to register tenant DB for {tenant.slug}: {e}")
        messages.error(request, "Could not connect to the school's database.")
        return redirect("tenants:master_dashboard")

    # Make sure there is at least one ADMIN-role account in the tenant DB.
    try:
        ensure_tenant_admin(tenant)
    except Exception as e:
        logger.exception(f"Failed to ensure admin for tenant {tenant.slug}: {e}")
        messages.error(request, "Could not verify the school's admin account.")
        return redirect("tenants:master_dashboard")

    alias = tenant.db_alias
    role_val = Role.ADMIN.value if hasattr(Role.ADMIN, 'value') else str(Role.ADMIN)
    admin_users = User.objects.using(alias).filter(role=role_val).order_by("id")

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        new_password = request.POST.get("new_password", "").strip()

        if not new_password or len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect("tenants:school_reset_password", slug=slug)

        target = None
        if user_id:
            try:
                target = admin_users.get(id=int(user_id))
            except (ValueError, TypeError, User.DoesNotExist):
                target = None

        if target is None:
            # The selected account is missing (e.g. stale/admin deleted) or the
            # tenant DB has no admin at all — never leave the school without a
            # working admin.  Fall back to / create the guaranteed admin record.
            target = admin_users.first()
            if target is not None:
                messages.info(
                    request,
                    "The selected account was not found; the existing admin account's "
                    "password was reset instead.",
                )

        if target is None:
            try:
                ensure_tenant_admin(tenant, admin_password=new_password)
                messages.success(
                    request,
                    f"Created a new admin account for '{tenant.school_name}' "
                    "and set its password.",
                )
                return redirect("tenants:master_dashboard")
            except Exception as e:
                logger.exception(f"Failed to create admin for tenant {tenant.slug}: {e}")
                messages.error(request, "Could not create the admin account.")
                return redirect("tenants:school_reset_password", slug=slug)

        target.set_password(new_password)
        target.save(using=alias, update_fields=["password"])
        messages.success(
            request,
            f"Password for '{target.username}' at {tenant.school_name} has been reset."
        )
        return redirect("tenants:master_dashboard")

    context = {
        "tenant": tenant,
        "admin_users": admin_users,
    }
    return render(request, "tenants/reset_password.html", context)


@superadmin_required
@require_POST
def school_delete(request, slug):
    """Hard-delete a tenant school and its database."""
    tenant = get_object_or_404(Tenant, slug=slug)
    school_name = tenant.school_name

    delete_tenant_db(tenant)
    tenant.delete()

    messages.success(request, f"School '{school_name}' and all its data have been permanently deleted.")
    return redirect("tenants:master_dashboard")
