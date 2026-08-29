"""Phase 10: User Account Management & ID Card views."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required
from apps.accounts.forms import CreateUserAccountForm, ResetPasswordForm
from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.students.models import Student
from apps.teachers.models import Teacher

User = get_user_model()


# ==============================================================================
# Helper utilities
# ==============================================================================

def _get_non_admin_user_queryset():
    """All Student/Teacher linked user accounts (excludes admin accounts)."""
    return User.objects.filter(role__in=[Role.STUDENT, Role.TEACHER]).select_related(
        "student_profile", "teacher_profile"
    ).order_by("-date_joined")


# ==============================================================================
# Phase 10.1 – User Account Management
# ==============================================================================

@admin_required
def account_list(request):
    """Central interface listing all Student/Teacher system accounts."""
    query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()
    status_filter = request.GET.get("status", "").strip()

    accounts_qs = _get_non_admin_user_queryset()

    if query:
        accounts_qs = accounts_qs.filter(
            Q(username__icontains=query)
            | Q(student_profile__name__icontains=query)
            | Q(student_profile__student_id__icontains=query)
            | Q(teacher_profile__name__icontains=query)
            | Q(teacher_profile__teacher_id__icontains=query)
        )
    if role_filter:
        accounts_qs = accounts_qs.filter(role=role_filter)
    if status_filter == "active":
        accounts_qs = accounts_qs.filter(is_active=True)
    elif status_filter == "disabled":
        accounts_qs = accounts_qs.filter(is_active=False)

    # Summary counts
    total_accounts = User.objects.filter(role__in=[Role.STUDENT, Role.TEACHER]).count()
    student_accounts = User.objects.filter(role=Role.STUDENT).count()
    teacher_accounts = User.objects.filter(role=Role.TEACHER).count()
    disabled_accounts = User.objects.filter(
        role__in=[Role.STUDENT, Role.TEACHER], is_active=False
    ).count()

    # Students & teachers WITHOUT accounts (for the create modal)
    students_without_account = Student.objects.filter(is_active=True, user__isnull=True).order_by("name")
    teachers_without_account = Teacher.objects.filter(is_active=True, user__isnull=True).order_by("name")

    paginator = Paginator(accounts_qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "query": query,
        "role_filter": role_filter,
        "status_filter": status_filter,
        "total_accounts": total_accounts,
        "student_accounts": student_accounts,
        "teacher_accounts": teacher_accounts,
        "disabled_accounts": disabled_accounts,
        "students_without_account": students_without_account,
        "teachers_without_account": teachers_without_account,
        "result_count": accounts_qs.count(),
        "create_form": CreateUserAccountForm(),
    }
    return render(request, "accounts/account_list.html", context)


@admin_required
def account_create(request):
    """Create and link a system user account to a Student or Teacher."""
    if request.method != "POST":
        return redirect("accounts:account_list")

    profile_type = request.POST.get("profile_type", "").strip()  # "student" or "teacher"
    profile_id_raw = request.POST.get("profile_id", "").strip()

    form = CreateUserAccountForm(request.POST)
    if not form.is_valid():
        messages.error(request, f"Could not create account: {form.errors.as_text()}")
        return redirect("accounts:account_list")

    try:
        profile_pk = int(profile_id_raw)
    except (TypeError, ValueError):
        messages.error(request, "Invalid profile specified.")
        return redirect("accounts:account_list")

    profile_model = {"student": Student, "teacher": Teacher}.get(profile_type)
    if profile_model is None:
        messages.error(request, "Invalid profile type specified.")
        return redirect("accounts:account_list")

    profile = get_object_or_404(profile_model, id=profile_pk)
    role = Role.STUDENT if profile_type == "student" else Role.TEACHER
    if profile.user_id:
        messages.warning(request, f"{profile.name} already has a linked account.")
        return redirect("accounts:account_list")

    username = form.cleaned_data["username"]
    password = form.cleaned_data["password1"]

    try:
        # Atomic: the login account and its profile link commit together, so a
        # failure can never leave an orphaned (unlinked) account behind.
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                role=role,
                is_active=True,
            )
            profile.user = user
            profile.save(update_fields=["user"])
    except IntegrityError:
        # Covers the rare race where the same username is claimed by another
        # request between the form-level uniqueness check and this INSERT.
        messages.error(
            request,
            f"Could not create account: the username <strong>{username}</strong> "
            "was just taken. Please choose a different one.",
        )
        return redirect("accounts:account_list")

    messages.success(
        request,
        f"Account <strong>{username}</strong> ({role}) created and linked to <strong>{profile.name}</strong>.",
    )
    return redirect("accounts:account_list")


@admin_required
def account_toggle_status(request, user_id):
    """Toggle a student/teacher account between Active and Disabled."""
    if request.method != "POST":
        return redirect("accounts:account_list")

    user = get_object_or_404(User, id=user_id, role__in=[Role.STUDENT, Role.TEACHER])
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    new_status = "activated" if user.is_active else "disabled"
    messages.success(request, f"Account <strong>{user.username}</strong> has been {new_status}.")
    return redirect("accounts:account_list")


@admin_required
def account_reset_password(request, user_id):
    """Admin password reset for a student/teacher account."""
    user_obj = get_object_or_404(User, id=user_id, role__in=[Role.STUDENT, Role.TEACHER])

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user_obj.set_password(form.cleaned_data["new_password1"])
            user_obj.save()
            messages.success(
                request,
                f"Password for account <strong>{user_obj.username}</strong> has been reset successfully.",
            )
            return redirect("accounts:account_list")
    else:
        form = ResetPasswordForm()

    context = {
        "form": form,
        "account_user": user_obj,
        "profile": (
            getattr(user_obj, "student_profile", None)
            or getattr(user_obj, "teacher_profile", None)
        ),
    }
    return render(request, "accounts/reset_password.html", context)


@admin_required
@require_POST
def account_delete(request, user_id):
    """Permanently delete a student/teacher user account (unlinks profile).

    Gracefully handles the case where the ``User`` account is already gone:

      1. If the User account exists, it is deleted as before (the linked
         Student/Teacher profile is kept but unlinked via ``SET_NULL``).
      2. If the User is missing, the view still looks for a matching
         Student/Teacher profile (by primary key or the orphaned user link) and
         deletes it safely — falling back to a soft-delete when fee/attendance
         history is protected, so the request never 404s.
      3. If nothing matches, a clean error message is shown instead of a 404.
    """
    user_obj = User.objects.filter(
        id=user_id, role__in=[Role.STUDENT, Role.TEACHER]
    ).first()
    if user_obj is not None:
        username = user_obj.username
        user_obj.delete()
        messages.success(
            request,
            f"Account <strong>{username}</strong> has been permanently deleted.",
        )
        return redirect("accounts:account_list")

    # No matching login account — the profile record may still exist (e.g. the
    # login account was deleted previously but the Student/Teacher was kept).
    student = Student.objects.filter(Q(pk=user_id) | Q(user_id=user_id)).first()
    if student is not None:
        student_id = student.student_id
        try:
            student.delete()
            message = (
                f"Linked account was already missing; student "
                f"<strong>{student.name}</strong> ({student_id}) has been deleted."
            )
        except ProtectedError:
            # Fee/attendance history protects the row — soft-delete instead so
            # financial & attendance records are preserved (same behaviour as
            # the Students list "delete" action).
            student.is_active = False
            student.save(update_fields=["is_active", "updated_at"])
            message = (
                f"Linked account was already missing; student "
                f"<strong>{student.name}</strong> ({student_id}) had protected "
                "fee/attendance history and was deactivated instead."
            )
        messages.success(request, message)
        return redirect("accounts:account_list")

    teacher = Teacher.objects.filter(Q(pk=user_id) | Q(user_id=user_id)).first()
    if teacher is not None:
        teacher_id = teacher.teacher_id
        try:
            teacher.delete()
            message = (
                f"Linked account was already missing; teacher "
                f"<strong>{teacher.name}</strong> ({teacher_id}) has been deleted."
            )
        except ProtectedError:
            teacher.is_active = False
            teacher.save(update_fields=["is_active", "updated_at"])
            message = (
                f"Linked account was already missing; teacher "
                f"<strong>{teacher.name}</strong> ({teacher_id}) had protected "
                "attendance history and was deactivated instead."
            )
        messages.success(request, message)
        return redirect("accounts:account_list")

    # Neither a user account nor a profile exists — handle gracefully.
    messages.error(
        request,
        f"No account or student/teacher record was found for id {user_id}.",
    )
    return redirect("accounts:account_list")


# ==============================================================================
# Phase 10.2 – Printable ID Card Views
# ==============================================================================

@admin_required
def id_card_student(request, student_id):
    """Render a single printable student ID card."""
    student = get_object_or_404(
        Student.objects.select_related("school_class"),
        student_id=student_id,
    )
    return render(request, "accounts/id_card_student.html", {"students": [student], "single": True})


@admin_required
def id_card_teacher(request, teacher_id):
    """Render a single printable teacher ID card."""
    teacher = get_object_or_404(
        Teacher.objects.prefetch_related("assigned_classes"),
        teacher_id=teacher_id,
    )
    return render(request, "accounts/id_card_teacher.html", {"teachers": [teacher], "single": True})


@admin_required
def id_card_batch_students(request):
    """Batch printable student ID cards (class-wise or all)."""
    class_id = request.GET.get("class_id", "").strip()
    classes = SchoolClass.objects.order_by("order", "id")

    students_qs = Student.objects.filter(is_active=True).select_related("school_class").order_by("school_class__order", "name")
    if class_id.isdigit():
        students_qs = students_qs.filter(school_class_id=int(class_id))

    students = list(students_qs)
    selected_class_id = int(class_id) if class_id.isdigit() else None

    context = {
        "students": students,
        "classes": classes,
        "selected_class_id": selected_class_id,
        "selected_class": SchoolClass.objects.filter(id=selected_class_id).first() if selected_class_id else None,
        "single": False,
    }
    return render(request, "accounts/id_card_student.html", context)


@admin_required
def id_card_batch_teachers(request):
    """Batch printable teacher ID cards."""
    teachers = Teacher.objects.filter(is_active=True).prefetch_related("assigned_classes").order_by("name")
    return render(request, "accounts/id_card_teacher.html", {"teachers": list(teachers), "single": False})
