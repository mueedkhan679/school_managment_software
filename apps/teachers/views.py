import base64
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required
from apps.classrooms.models import SchoolClass
from apps.core.constants import MONTHS, MONTHS_MAP
from .forms import TeacherForm, TeacherSalaryForm
from .models import (
    SalaryStatus,
    Teacher,
    TeacherAttendance,
    TeacherAttendanceStatus,
    TeacherSalary,
)


def _get_teacher(teacher_id_or_pk):
    """Helper to retrieve a Teacher by TCH-* identifier or numeric primary key."""
    if str(teacher_id_or_pk).isdigit():
        return get_object_or_404(
            Teacher.objects.prefetch_related("assigned_classes"),
            id=int(teacher_id_or_pk),
        )
    return get_object_or_404(
        Teacher.objects.prefetch_related("assigned_classes"),
        teacher_id=teacher_id_or_pk,
    )


# ==============================================================================
# Phase 8: Teacher Management Views
# ==============================================================================

@admin_required
def teacher_list(request):
    """List all teachers with search and class/status filters."""
    query = request.GET.get("q", "").strip()
    class_id = request.GET.get("class_id", "").strip()
    status_filter = request.GET.get("status", "active").strip()

    teachers = Teacher.objects.prefetch_related("assigned_classes").order_by("teacher_id")

    # Status filtering
    if status_filter == "active":
        teachers = teachers.filter(is_active=True)
    elif status_filter == "inactive":
        teachers = teachers.filter(is_active=False)

    # Class filter
    if class_id.isdigit():
        teachers = teachers.filter(assigned_classes__id=int(class_id)).distinct()

    # Search filter
    if query:
        teachers = teachers.filter(
            Q(teacher_id__icontains=query)
            | Q(name__icontains=query)
            | Q(cnic__icontains=query)
            | Q(phone__icontains=query)
        ).distinct()

    # Counts & Financial Payroll Summary
    total_teachers = Teacher.objects.count()
    active_teachers = Teacher.objects.filter(is_active=True).count()
    inactive_teachers = total_teachers - active_teachers
    total_monthly_payroll = (
        Teacher.objects.filter(is_active=True).aggregate(total=Sum("monthly_salary"))["total"]
        or Decimal("0.00")
    )
    total_yearly_payroll = total_monthly_payroll * 12

    # Pagination
    paginator = Paginator(teachers, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    classes = SchoolClass.objects.order_by("order", "id")

    context = {
        "page_obj": page_obj,
        "classes": classes,
        "query": query,
        "selected_class": int(class_id) if class_id.isdigit() else None,
        "selected_status": status_filter,
        "total_teachers": total_teachers,
        "active_teachers": active_teachers,
        "inactive_teachers": inactive_teachers,
        "total_monthly_payroll": total_monthly_payroll,
        "total_yearly_payroll": total_yearly_payroll,
        "result_count": teachers.count(),
    }
    return render(request, "teachers/list.html", context)


@admin_required
def teacher_create(request):
    """Register a new teacher with atomic TCH-00000X auto ID generation."""
    if request.method == "POST":
        form = TeacherForm(request.POST, request.FILES)
        if form.is_valid():
            teacher = form.save()
            messages.success(
                request,
                f"Teacher '{teacher.name}' registered successfully with ID {teacher.teacher_id}.",
            )
            return redirect("teachers:detail", teacher_id=teacher.teacher_id)
    else:
        form = TeacherForm()

    context = {
        "form": form,
        "title": "Register New Teacher",
        "action_text": "Register Teacher",
    }
    return render(request, "teachers/form.html", context)


@admin_required
def teacher_detail(request, teacher_id):
    """View complete teacher profile, assigned classes, CNIC images, and salary history."""
    teacher = _get_teacher(teacher_id)
    salaries = teacher.salaries.order_by("-salary_year", "-salary_month", "-payment_date")

    # Financial stats
    paid_salaries = salaries.filter(status=SalaryStatus.PAID)
    total_paid_all_time = (
        paid_salaries.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )

    current_year = timezone.now().year
    curr_year_paid = (
        paid_salaries.filter(salary_year=current_year).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    yearly_expected_salary = teacher.yearly_salary
    yearly_pending = max(Decimal("0.00"), yearly_expected_salary - curr_year_paid)

    # 12-month calendar schedule for salaries in current_year
    paid_months_set = set(
        paid_salaries.filter(salary_year=current_year).values_list("salary_month", flat=True)
    )
    salaries_schedule = []
    for m_num, m_name in MONTHS:
        salaries_schedule.append({
            "month_num": m_num,
            "month_name": m_name,
            "is_paid": m_num in paid_months_set,
        })

    context = {
        "teacher": teacher,
        "assigned_classes": teacher.assigned_classes.all(),
        "salaries": salaries[:24],
        "salaries_schedule": salaries_schedule,
        "total_paid_all_time": total_paid_all_time,
        "curr_year_paid": curr_year_paid,
        "yearly_expected_salary": yearly_expected_salary,
        "yearly_pending": yearly_pending,
        "current_year": current_year,
    }
    return render(request, "teachers/detail.html", context)


@admin_required
def teacher_update(request, teacher_id):
    """Edit teacher details, salary, assigned classes, and photos."""
    teacher = _get_teacher(teacher_id)
    if request.method == "POST":
        form = TeacherForm(request.POST, request.FILES, instance=teacher)
        if form.is_valid():
            teacher = form.save()
            messages.success(
                request, f"Profile for '{teacher.name}' ({teacher.teacher_id}) updated successfully."
            )
            return redirect("teachers:detail", teacher_id=teacher.teacher_id)
    else:
        form = TeacherForm(instance=teacher)

    context = {
        "form": form,
        "teacher": teacher,
        "title": f"Edit Teacher: {teacher.name} ({teacher.teacher_id})",
        "action_text": "Save Changes",
    }
    return render(request, "teachers/form.html", context)


@admin_required
@require_POST
def teacher_delete(request, teacher_id):
    """Soft-delete teacher (is_active=False) preserving salary and attendance history."""
    teacher = _get_teacher(teacher_id)
    teacher.is_active = False
    teacher.save(update_fields=["is_active", "updated_at"])
    messages.success(
        request,
        f"Teacher '{teacher.name}' ({teacher.teacher_id}) has been archived/deactivated. "
        "Salary history and financial records remain fully intact.",
    )
    return redirect("teachers:list")


@admin_required
@require_POST
def teacher_restore(request, teacher_id):
    """Restore an archived teacher to active status."""
    teacher = _get_teacher(teacher_id)
    teacher.is_active = True
    teacher.save(update_fields=["is_active", "updated_at"])
    messages.success(
        request,
        f"Teacher '{teacher.name}' ({teacher.teacher_id}) has been restored to active status.",
    )
    return redirect("teachers:detail", teacher_id=teacher.teacher_id)


# ==============================================================================
# Phase 9: Teacher Salary Management Views
# ==============================================================================

@admin_required
def salary_list(request):
    """List all teacher salary disbursements with search and multi-filtering."""
    now = timezone.now()
    current_year = now.year
    current_month = now.month

    query = request.GET.get("q", "").strip()
    month_filter = request.GET.get("month", "").strip()
    year_filter = request.GET.get("year", "").strip()
    status_filter = request.GET.get("status", "").strip()

    salaries = TeacherSalary.objects.select_related("teacher", "recorded_by").order_by(
        "-payment_date", "-salary_year", "-salary_month", "-id"
    )

    # Search
    if query:
        salaries = salaries.filter(
            Q(teacher__teacher_id__icontains=query)
            | Q(teacher__name__icontains=query)
            | Q(reference__icontains=query)
        )

    # Filters
    if month_filter.isdigit():
        salaries = salaries.filter(salary_month=int(month_filter))

    if year_filter.isdigit():
        salaries = salaries.filter(salary_year=int(year_filter))

    if status_filter:
        salaries = salaries.filter(status=status_filter)

    # Financial Aggregates
    filtered_total = (
        salaries.filter(status=SalaryStatus.PAID).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    month_total = (
        TeacherSalary.objects.filter(
            salary_year=current_year,
            salary_month=current_month,
            status=SalaryStatus.PAID,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    year_total = (
        TeacherSalary.objects.filter(
            salary_year=current_year,
            status=SalaryStatus.PAID,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # Pagination
    paginator = Paginator(salaries, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    available_years = list(range(current_year - 2, current_year + 3))

    context = {
        "page_obj": page_obj,
        "months": MONTHS,
        "available_years": available_years,
        "query": query,
        "selected_month": int(month_filter) if month_filter.isdigit() else None,
        "selected_year": int(year_filter) if year_filter.isdigit() else None,
        "selected_status": status_filter,
        "filtered_total": filtered_total,
        "month_total": month_total,
        "year_total": year_total,
        "current_month_name": MONTHS_MAP.get(current_month, ""),
        "current_year": current_year,
        "result_count": salaries.count(),
    }
    return render(request, "teachers/salary_list.html", context)


@admin_required
def salary_create(request):
    """Record a teacher salary payment."""
    if request.method == "POST":
        form = TeacherSalaryForm(request.POST)
        if form.is_valid():
            salary = form.save(commit=False)
            salary.recorded_by = request.user
            salary.save()
            messages.success(
                request,
                f"Salary payment of Rs {salary.amount:.2f} for {salary.teacher.name} "
                f"({salary.get_salary_month_display()} {salary.salary_year}) recorded successfully.",
            )
            return redirect("teachers:salary_voucher", pk=salary.pk)
    else:
        initial = {}
        teacher_param = request.GET.get("teacher_id") or request.GET.get("teacher")
        if teacher_param:
            if str(teacher_param).isdigit():
                teacher = Teacher.objects.filter(id=int(teacher_param)).first()
            else:
                teacher = Teacher.objects.filter(teacher_id=teacher_param).first()

            if teacher:
                initial["teacher"] = teacher.pk
                initial["amount"] = teacher.monthly_salary

        month_param = request.GET.get("month")
        if month_param and month_param.isdigit():
            initial["salary_month"] = int(month_param)
        year_param = request.GET.get("year")
        if year_param and year_param.isdigit():
            initial["salary_year"] = int(year_param)

        form = TeacherSalaryForm(initial=initial)

    context = {
        "form": form,
        "title": "Disburse Teacher Salary",
        "action_text": "Disburse Salary & Issue Payslip",
    }
    return render(request, "teachers/salary_form.html", context)


@admin_required
def salary_voucher(request, pk):
    """Printable official salary payslip voucher."""
    salary = get_object_or_404(
        TeacherSalary.objects.select_related("teacher", "recorded_by"),
        pk=pk,
    )
    teacher = salary.teacher

    # Salary financial summary
    paid_salaries = teacher.salaries.filter(status=SalaryStatus.PAID)
    total_paid_all_time = (
        paid_salaries.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )
    curr_year_paid = (
        paid_salaries.filter(salary_year=salary.salary_year).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    yearly_expected = teacher.yearly_salary
    yearly_pending = max(Decimal("0.00"), yearly_expected - curr_year_paid)

    context = {
        "salary": salary,
        "teacher": teacher,
        "total_paid_all_time": total_paid_all_time,
        "curr_year_paid": curr_year_paid,
        "yearly_expected": yearly_expected,
        "yearly_pending": yearly_pending,
    }
    return render(request, "teachers/salary_voucher.html", context)


@admin_required
def salary_update(request, pk):
    """Edit an existing teacher salary transaction."""
    salary = get_object_or_404(TeacherSalary, pk=pk)
    if request.method == "POST":
        form = TeacherSalaryForm(request.POST, instance=salary)
        if form.is_valid():
            salary = form.save()
            messages.success(
                request,
                f"Salary record for {salary.teacher.name} ({salary.get_salary_month_display()} {salary.salary_year}) updated.",
            )
            return redirect("teachers:salary_voucher", pk=salary.pk)
    else:
        form = TeacherSalaryForm(instance=salary)

    context = {
        "form": form,
        "salary": salary,
        "title": f"Edit Salary: {salary.teacher.name} ({salary.get_salary_month_display()} {salary.salary_year})",
        "action_text": "Save Changes",
    }
    return render(request, "teachers/salary_form.html", context)


@admin_required
@require_POST
def salary_delete(request, pk):
    """Delete a salary record."""
    salary = get_object_or_404(TeacherSalary, pk=pk)
    teacher_name = salary.teacher.name
    month_display = salary.get_salary_month_display()
    year = salary.salary_year
    salary.delete()
    messages.success(
        request,
        f"Salary record for {teacher_name} ({month_display} {year}) has been deleted.",
    )
    return redirect("teachers:salary_list")


@admin_required
def api_teacher_salary_info(request, teacher_id):
    """Return JSON information for a teacher's monthly base salary and paid months for dynamic prefilling."""
    teacher = get_object_or_404(Teacher, id=teacher_id)
    year = int(request.GET.get("year", timezone.now().year))

    paid_months = list(
        teacher.salaries.filter(salary_year=year, status=SalaryStatus.PAID).values_list(
            "salary_month", flat=True
        )
    )

    data = {
        "teacher_id": teacher.teacher_id,
        "name": teacher.name,
        "monthly_salary": float(teacher.monthly_salary),
        "yearly_salary": float(teacher.yearly_salary),
        "paid_months": paid_months,
    }
    return JsonResponse(data)


# ---------------------------------------------------------------------------
# Dynamic QR — Teacher self attendance check-in
# ---------------------------------------------------------------------------

def _today_token():
    """Generate today's signed QR payload."""
    from apps.attendance.qr_tokens import generate_token

    return generate_token(timezone.localdate())


def _qr_png_bytes(token: str) -> bytes:
    import io

    import qrcode

    buffer = io.BytesIO()
    image = qrcode.make(token, box_size=8, border=2)
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@admin_required
def teacher_attendance_qr_page(request):
    """Full-page live QR code for teacher self check-in."""
    token = _today_token()
    context = {
        "qr_data_uri": "data:image/png;base64," + base64.b64encode(
            _qr_png_bytes(token)
        ).decode(),
        "token": token,
        "today": timezone.localdate(),
    }
    return render(request, "teachers/attendance_qr.html", context)


@admin_required
def teacher_attendance_qr_png(request):
    """Raw PNG of today's QR token — embedded by the dashboard widget."""
    response = HttpResponse(content_type="image/png")
    response.write(_qr_png_bytes(_today_token()))
    return response


def _parse_iso_date(value: str):
    """Parse a YYYY-MM-DD string into a date, or None when invalid."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@admin_required
def teacher_attendance_list(request):
    """Teacher Attendance Record register with date/teacher/status filters.

    Supports three date modes via ``range``: ``today``, ``specific`` (with
    ``date=YYYY-MM-DD``) and ``custom`` (with ``from``/``to``). An empty range
    shows the full history. Also filterable by teacher and status.

    When today's closing time has passed, missing active teachers are
    automatically marked Absent (Auto-System) before the page renders.
    """
    # Friendly safety: trigger the auto-absent pass for today after cut-off.
    from apps.teachers.auto_absent import mark_auto_absent

    mark_auto_absent()

    records = TeacherAttendance.objects.select_related("teacher")

    range_mode = request.GET.get("range", "").strip()
    specific_raw = request.GET.get("date", "").strip()
    from_raw = request.GET.get("from", "").strip()
    to_raw = request.GET.get("to", "").strip()
    teacher_param = request.GET.get("teacher", "").strip()
    status_filter = request.GET.get("status", "").strip()

    today = timezone.localdate()
    date_from = _parse_iso_date(from_raw)
    date_to = _parse_iso_date(to_raw)
    specific_date = _parse_iso_date(specific_raw)

    if range_mode == "today":
        records = records.filter(date=today)
        range_label = f"Today ({today.strftime('%b j, Y')})"
    elif range_mode == "specific" and specific_date:
        records = records.filter(date=specific_date)
        range_label = specific_date.strftime("%b j, Y")
    elif range_mode == "custom" and (date_from or date_to):
        if date_from:
            records = records.filter(date__gte=date_from)
        if date_to:
            records = records.filter(date__lte=date_to)
        start_label = date_from.strftime("%b j") if date_from else "…"
        end_label = date_to.strftime("%b j, Y") if date_to else "…"
        range_label = f"{start_label} – {end_label}"
    else:
        range_mode = ""
        range_label = "All Time"

    selected_teacher_id = int(teacher_param) if teacher_param.isdigit() else None
    if selected_teacher_id:
        records = records.filter(teacher_id=selected_teacher_id)

    valid_statuses = {c[0] for c in TeacherAttendanceStatus.choices}
    if status_filter in valid_statuses:
        records = records.filter(status=status_filter)

    summary = records.aggregate(
        total=models.Count("id"),
        present=models.Count("id", filter=models.Q(status="PRESENT")),
        absent=models.Count("id", filter=models.Q(status="ABSENT")),
        leave=models.Count("id", filter=models.Q(status="LEAVE")),
    )

    paginator = Paginator(records.order_by("-date", "teacher__teacher_id"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    teachers = Teacher.objects.filter(is_active=True).order_by("name")

    context = {
        "page_obj": page_obj,
        "teachers": teachers,
        "range_mode": range_mode,
        "range_label": range_label,
        "specific_date": specific_raw,
        "date_from": from_raw,
        "date_to": to_raw,
        "selected_teacher": selected_teacher_id,
        "selected_status": status_filter,
        **summary,
    }
    return render(request, "teachers/attendance_list.html", context)
