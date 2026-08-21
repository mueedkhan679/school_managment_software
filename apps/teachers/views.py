from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required
from apps.classrooms.models import SchoolClass
from apps.core.constants import MONTHS, MONTHS_MAP
from .forms import TeacherForm, TeacherSalaryForm
from .models import SalaryStatus, Teacher, TeacherSalary


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
