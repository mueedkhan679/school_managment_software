"""Master Admin Portal views for Super-Admin school management."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import connections
import logging

logger = logging.getLogger("tenants.admin_views")
from django.views.decorators.http import require_POST

from apps.accounts.models import Role

from .decorators import superadmin_required
from .models import Tenant
from .utils import delete_tenant_db, provision_tenant_db, register_tenant_db

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
    }
    return render(request, "tenants/master_dashboard.html", context)


@superadmin_required
def school_add(request):
    """Create a new tenant school and provision its database."""
    if request.method == "POST":
        school_name = request.POST.get("school_name", "").strip()
        slug = request.POST.get("slug", "").strip().lower().replace(" ", "-")
        admin_email = request.POST.get("admin_email", "").strip()
        admin_phone = request.POST.get("admin_phone", "").strip()
        max_students = request.POST.get("max_students", "500").strip()

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

        tenant = Tenant.objects.create(
            school_name=school_name,
            slug=slug,
            admin_email=admin_email,
            admin_phone=admin_phone,
            max_students=int(max_students) if max_students.isdigit() else 500,
        )

        # Provision the tenant database (create DB, run migrations, seed admin user)
        admin_username = provision_tenant_db(tenant)

        messages.success(
            request,
            f"School '{tenant.school_name}' created successfully! "
            f"Database provisioned. Default admin: {admin_username} / changeme123"
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
def school_reset_password(request, slug):
    """Forcibly reset a school admin's password."""
    tenant = get_object_or_404(Tenant, slug=slug)

    # Ensure tenant DB is registered
    register_tenant_db(tenant)
    alias = tenant.db_alias
    admin_users = User.objects.none()

    if alias in connections.databases:
        try:
            # 2. Extract role properly
            role_val = Role.ADMIN.value if hasattr(Role.ADMIN, 'value') else str(Role.ADMIN)
            
            # 3. Robust query with fallback
            admin_users = User.objects.using(alias).filter(role=role_val)
            if not admin_users.exists():
                admin_users = User.objects.using(alias).filter(username__startswith='admin_')
        except Exception as e:
            logger.exception(f"Failed to fetch admin users for tenant {tenant.slug}: {e}")

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        new_password = request.POST.get("new_password", "").strip()

        if not new_password or len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect("tenants:school_reset_password", slug=slug)

        try:
            target_user = User.objects.using(alias).get(id=int(user_id))
            target_user.set_password(new_password)
            target_user.save(using=alias, update_fields=["password"])
            messages.success(
                request,
                f"Password for '{target_user.username}' at {tenant.school_name} has been reset."
            )
            return redirect("tenants:master_dashboard")
        except Exception as e:
            logger.exception(f"Error resetting password for user {user_id} in {tenant.slug}: {e}")
            messages.error(request, "Error resetting password.")

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
