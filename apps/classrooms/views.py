from django.contrib import messages
from django.db import models
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required
from .forms import SchoolClassForm
from .models import SchoolClass


@admin_required
def class_list(request):
    """List all classes with student counts, fee structure, and assigned teachers."""
    form = SchoolClassForm()
    classes = (
        SchoolClass.objects.annotate(
            active_students_count=models.Count(
                "students",
                filter=Q(students__is_active=True),
            ),
            total_students_count=models.Count("students"),
        )
        .prefetch_related("assigned_teachers")
        .order_by("order", "id")
    )

    total_classes = classes.count()
    total_enrolled = sum(c.active_students_count for c in classes)

    context = {
        "classes": classes,
        "total_classes": total_classes,
        "total_enrolled": total_enrolled,
        "form": form,
    }
    return render(request, "classrooms/list.html", context)


@admin_required
@require_POST
def class_create(request):
    """Handle creation of a new SchoolClass."""
    form = SchoolClassForm(request.POST)
    if form.is_valid():
        school_class = form.save()
        messages.success(
            request, f"Class '{school_class.name}' has been created successfully."
        )
        return redirect("classrooms:list")
    
    # If invalid, re-render the list page with the form errors and open modal
    classes = (
        SchoolClass.objects.annotate(
            active_students_count=models.Count(
                "students",
                filter=Q(students__is_active=True),
            ),
            total_students_count=models.Count("students"),
        )
        .prefetch_related("assigned_teachers")
        .order_by("order", "id")
    )
    context = {
        "classes": classes,
        "total_classes": classes.count(),
        "total_enrolled": sum(c.active_students_count for c in classes),
        "form": form,
        "modal_open": True,
    }
    messages.error(request, "Please correct the errors in the form.")
    return render(request, "classrooms/list.html", context, status=400)


@admin_required
def class_detail(request, pk):
    """View detailed information about a class, assigned teachers, and enrolled students."""
    school_class = get_object_or_404(
        SchoolClass.objects.prefetch_related("assigned_teachers"),
        pk=pk,
    )
    students = school_class.students.order_by("student_id")
    active_students = [s for s in students if s.is_active]
    inactive_students = [s for s in students if not s.is_active]
    
    # Calculate potential monthly tuition generated from this class
    expected_monthly_income = sum(s.effective_monthly_fee for s in active_students)
    expected_yearly_income = expected_monthly_income * 12

    context = {
        "school_class": school_class,
        "students": students,
        "active_students": active_students,
        "inactive_students": inactive_students,
        "active_count": len(active_students),
        "total_count": len(students),
        "expected_monthly_income": expected_monthly_income,
        "expected_yearly_income": expected_yearly_income,
        "assigned_teachers": school_class.assigned_teachers.filter(is_active=True),
    }
    return render(request, "classrooms/detail.html", context)


@admin_required
def class_update(request, pk):
    """Edit class details (name, order, monthly fee)."""
    school_class = get_object_or_404(SchoolClass, pk=pk)
    if request.method == "POST":
        form = SchoolClassForm(request.POST, instance=school_class)
        if form.is_valid():
            school_class = form.save()
            messages.success(
                request, f"Class '{school_class.name}' updated successfully."
            )
            return redirect("classrooms:detail", pk=school_class.pk)
    else:
        form = SchoolClassForm(instance=school_class)

    context = {
        "form": form,
        "school_class": school_class,
    }
    return render(request, "classrooms/form.html", context)


@admin_required
@require_POST
def class_delete(request, pk):
    """Safely delete a class if no students are enrolled in it."""
    school_class = get_object_or_404(SchoolClass, pk=pk)
    name = school_class.name
    student_count = school_class.students.count()

    if student_count > 0:
        messages.error(
            request,
            f"Cannot delete class '{name}' because {student_count} student(s) are linked to it. "
            "Reassign or delete all enrolled students first to maintain data integrity.",
        )
        return redirect("classrooms:list")

    try:
        school_class.delete()
        messages.success(request, f"Class '{name}' has been deleted successfully.")
    except ProtectedError:
        messages.error(
            request,
            f"Cannot delete class '{name}' because related records depend on it.",
        )

    return redirect("classrooms:list")
