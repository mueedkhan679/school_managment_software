from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required
from apps.attendance.models import AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.fees.models import FeeStatus
from .forms import StudentForm
from .models import Student


def _get_student(student_id_or_pk):
    """Helper to retrieve a student by STU-* identifier or numeric primary key."""
    if str(student_id_or_pk).isdigit():
        return get_object_or_404(
            Student.objects.select_related("school_class"), id=int(student_id_or_pk)
        )
    return get_object_or_404(
        Student.objects.select_related("school_class"), student_id=student_id_or_pk
    )


@admin_required
def student_list(request):
    """List all students with search by ID/Name/Father/B-Form/Phone and filtering by Class & Status."""
    query = request.GET.get("q", "").strip()
    class_id = request.GET.get("class_id", "").strip()
    status_filter = request.GET.get("status", "active").strip()

    students = Student.objects.select_related("school_class").order_by("student_id")

    # Status filtering
    if status_filter == "active":
        students = students.filter(is_active=True)
    elif status_filter == "inactive":
        students = students.filter(is_active=False)
    # 'all' shows both active and inactive

    # Class filtering
    if class_id.isdigit():
        students = students.filter(school_class_id=int(class_id))

    # Search filtering
    if query:
        students = students.filter(
            Q(student_id__icontains=query)
            | Q(name__icontains=query)
            | Q(father_name__icontains=query)
            | Q(form_b_number__icontains=query)
            | Q(phone__icontains=query)
        )

    # Statistics counts
    total_students_count = Student.objects.count()
    active_students_count = Student.objects.filter(is_active=True).count()
    inactive_students_count = total_students_count - active_students_count

    # Pagination
    paginator = Paginator(students, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    classes = SchoolClass.objects.order_by("order", "id")

    context = {
        "page_obj": page_obj,
        "classes": classes,
        "query": query,
        "selected_class": int(class_id) if class_id.isdigit() else None,
        "selected_status": status_filter,
        "total_students_count": total_students_count,
        "active_students_count": active_students_count,
        "inactive_students_count": inactive_students_count,
        "result_count": students.count(),
    }
    return render(request, "students/list.html", context)


@admin_required
def student_create(request):
    """Register a new student with atomic STU-00000X auto ID generation."""
    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()
            messages.success(
                request,
                f"Student '{student.name}' registered successfully with ID {student.student_id}.",
            )
            return redirect("students:detail", student_id=student.student_id)
    else:
        # Preselect class if passed in GET param
        initial = {}
        class_id = request.GET.get("class_id")
        if class_id and class_id.isdigit():
            initial["school_class"] = int(class_id)
        form = StudentForm(initial=initial)

    context = {
        "form": form,
        "title": "Register New Student",
        "action_text": "Complete Admission",
    }
    return render(request, "students/form.html", context)


@admin_required
def student_detail(request, student_id):
    """View complete profile, fee history, and attendance records for a student."""
    student = _get_student(student_id)

    # Fee history and summary
    fees = student.fees.order_by("-fee_year", "-fee_month", "-payment_date")
    paid_fees = fees.filter(status=FeeStatus.PAID)
    total_paid_fees = paid_fees.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    current_year = timezone.now().year
    curr_year_paid = (
        paid_fees.filter(fee_year=current_year).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    yearly_expected = student.yearly_fee
    yearly_pending = max(Decimal("0.00"), yearly_expected - curr_year_paid)

    # Attendance history and rate
    attendance_records = student.attendance_records.order_by("-date")
    total_attendance_days = attendance_records.count()
    present_count = attendance_records.filter(status=AttendanceStatus.PRESENT).count()
    absent_count = attendance_records.filter(status=AttendanceStatus.ABSENT).count()
    leave_count = attendance_records.filter(status=AttendanceStatus.LEAVE).count()
    if total_attendance_days > 0:
        attendance_rate = round((present_count / total_attendance_days) * 100, 1)
    else:
        attendance_rate = 0.0

    # Detailed absent / leave log (exact dates, newest first)
    absent_leave_records = attendance_records.filter(
        status__in=[AttendanceStatus.ABSENT, AttendanceStatus.LEAVE]
    )

    # 12-month schedule for current year
    paid_month_map = {
        f.fee_month: f
        for f in paid_fees.filter(fee_year=current_year)
    }
    from apps.core.constants import MONTHS
    months_schedule = []
    for m_num, m_name in MONTHS:
        fee_entry = paid_month_map.get(m_num)
        months_schedule.append({
            "month_num": m_num,
            "month_name": m_name,
            "is_paid": bool(fee_entry),
            "fee": fee_entry,
        })

    context = {
        "student": student,
        "fees": fees[:24],  # Recent 24 entries
        "months_schedule": months_schedule,
        "total_paid_fees": total_paid_fees,
        "curr_year_paid": curr_year_paid,
        "yearly_expected": yearly_expected,
        "yearly_pending": yearly_pending,
        "attendance_records": attendance_records[:30],  # Recent 30 days
        "absent_leave_records": absent_leave_records,
        "total_attendance_days": total_attendance_days,
        "present_count": present_count,
        "absent_count": absent_count,
        "leave_count": leave_count,
        "attendance_rate": attendance_rate,
        "current_year": current_year,
    }
    return render(request, "students/detail.html", context)


@admin_required
def student_update(request, student_id):
    """Edit student profile details and photo."""
    student = _get_student(student_id)
    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            student = form.save()
            messages.success(
                request, f"Profile for student '{student.name}' ({student.student_id}) updated successfully."
            )
            return redirect("students:detail", student_id=student.student_id)
    else:
        form = StudentForm(instance=student)

    context = {
        "form": form,
        "student": student,
        "title": f"Edit Student: {student.name} ({student.student_id})",
        "action_text": "Save Changes",
    }
    return render(request, "students/form.html", context)


@admin_required
@require_POST
def student_delete(request, student_id):
    """Soft-delete student (is_active=False) preserving financial and attendance history."""
    student = _get_student(student_id)
    student.is_active = False
    student.save(update_fields=["is_active", "updated_at"])
    messages.success(
        request,
        f"Student '{student.name}' ({student.student_id}) has been deactivated (soft-deleted). "
        "Historical fee and attendance records remain fully preserved.",
    )
    return redirect("students:list")


@admin_required
@require_POST
def student_restore(request, student_id):
    """Reactivate a previously soft-deleted student."""
    student = _get_student(student_id)
    student.is_active = True
    student.save(update_fields=["is_active", "updated_at"])
    messages.success(
        request,
        f"Student '{student.name}' ({student.student_id}) has been restored to active status.",
    )
    return redirect("students:detail", student_id=student.student_id)
