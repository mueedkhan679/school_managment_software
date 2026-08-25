from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required
from apps.classrooms.models import SchoolClass
from apps.core.constants import MONTHS, MONTHS_MAP
from apps.students.models import Student
from .forms import StudentFeeForm
from .models import FeeStatus, StudentFee


def _build_defaulter_matrix(students, year):
    """Build month-by-month paid/unpaid matrix rows for the given students.

    Every active student appears exactly once with all 12 months of ``year``
    present: a month counts as PAID only when a PAID fee record exists,
    otherwise it is flagged as unpaid/defaulter. Returns ``(rows, summary)``
    where *rows* are template-ready dicts and *summary* carries aggregate
    counts for the stat cards / print footer.
    """
    year_fees = StudentFee.objects.filter(
        student__in=students, fee_year=year, status=FeeStatus.PAID
    ).values_list("student_id", "fee_month")
    paid_lookup = {}
    for student_id, fee_month in year_fees:
        paid_lookup.setdefault(student_id, set()).add(fee_month)

    defaulter_count = 0
    cleared_count = 0
    rows = []
    for student in students:
        paid_months = paid_lookup.get(student.pk, set())
        months = [
            {"num": num, "name": MONTHS_MAP[num][:3], "paid": num in paid_months}
            for num in range(1, 13)
        ]
        unpaid_count = 12 - len(paid_months)
        if unpaid_count:
            defaulter_count += 1
        else:
            cleared_count += 1
        rows.append(
            {
                "student": student,
                "months": months,
                "unpaid_count": unpaid_count,
            }
        )

    summary = {
        "total_students": len(rows),
        "defaulter_count": defaulter_count,
        "cleared_count": cleared_count,
    }
    return rows, summary


@admin_required
def fee_list(request):
    """List all student fee records with search and multi-criteria filtering."""
    now = timezone.now()
    current_year = now.year
    current_month = now.month

    query = request.GET.get("q", "").strip()
    month_filter = request.GET.get("month", "").strip()
    year_filter = request.GET.get("year", "").strip()
    class_filter = request.GET.get("class_id", "").strip()
    status_filter = request.GET.get("status", "").strip()

    fees = StudentFee.objects.select_related(
        "student", "student__school_class", "recorded_by"
    ).order_by("-payment_date", "-fee_year", "-fee_month", "-id")

    # Search query
    if query:
        fees = fees.filter(
            Q(student__student_id__icontains=query)
            | Q(student__name__icontains=query)
            | Q(student__father_name__icontains=query)
            | Q(reference__icontains=query)
        )

    # Filters
    if month_filter.isdigit():
        fees = fees.filter(fee_month=int(month_filter))

    if year_filter.isdigit():
        fees = fees.filter(fee_year=int(year_filter))

    if class_filter.isdigit():
        fees = fees.filter(student__school_class_id=int(class_filter))

    if status_filter:
        fees = fees.filter(status=status_filter)

    # Financial Aggregates
    filtered_total = (
        fees.filter(status=FeeStatus.PAID).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    month_total = (
        StudentFee.objects.filter(
            fee_year=current_year,
            fee_month=current_month,
            status=FeeStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    year_total = (
        StudentFee.objects.filter(
            fee_year=current_year,
            status=FeeStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    pending_count = fees.filter(status=FeeStatus.PENDING).count()

    # Pagination
    paginator = Paginator(fees, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    classes = SchoolClass.objects.order_by("order", "id")
    available_years = list(range(current_year - 2, current_year + 3))

    context = {
        "page_obj": page_obj,
        "classes": classes,
        "months": MONTHS,
        "available_years": available_years,
        "query": query,
        "selected_month": int(month_filter) if month_filter.isdigit() else None,
        "selected_year": int(year_filter) if year_filter.isdigit() else None,
        "selected_class": int(class_filter) if class_filter.isdigit() else None,
        "selected_status": status_filter,
        "filtered_total": filtered_total,
        "month_total": month_total,
        "year_total": year_total,
        "pending_count": pending_count,
        "current_month_name": MONTHS_MAP.get(current_month, ""),
        "current_year": current_year,
        "result_count": fees.count(),
    }
    return render(request, "fees/list.html", context)


@admin_required
def fee_create(request):
    """Record a new fee collection."""
    if request.method == "POST":
        form = StudentFeeForm(request.POST)
        if form.is_valid():
            fee = form.save(commit=False)
            fee.recorded_by = request.user
            fee.save()
            messages.success(
                request,
                f"Fee payment of Rs {fee.amount:.2f} for {fee.student.name} "
                f"({fee.get_fee_month_display()} {fee.fee_year}) has been recorded successfully.",
            )
            return redirect("fees:voucher", pk=fee.pk)
    else:
        initial = {}
        # Pre-select student if student_id or pk is passed in GET
        student_param = request.GET.get("student_id") or request.GET.get("student")
        if student_param:
            if str(student_param).isdigit():
                student = Student.objects.filter(id=int(student_param)).first()
            else:
                student = Student.objects.filter(student_id=student_param).first()

            if student:
                initial["student"] = student.pk
                initial["amount"] = student.effective_monthly_fee

        # Pre-select month or year if specified
        month_param = request.GET.get("month")
        if month_param and month_param.isdigit():
            initial["fee_month"] = int(month_param)
        year_param = request.GET.get("year")
        if year_param and year_param.isdigit():
            initial["fee_year"] = int(year_param)

        form = StudentFeeForm(initial=initial)

    context = {
        "form": form,
        "title": "Record Student Fee Payment",
        "action_text": "Collect Fee & Generate Receipt",
    }
    return render(request, "fees/form.html", context)


@admin_required
def fee_update(request, pk):
    """Edit an existing fee payment record."""
    fee = get_object_or_404(StudentFee, pk=pk)
    if request.method == "POST":
        form = StudentFeeForm(request.POST, instance=fee)
        if form.is_valid():
            fee = form.save()
            messages.success(
                request,
                f"Fee record for {fee.student.name} ({fee.get_fee_month_display()} {fee.fee_year}) updated successfully.",
            )
            return redirect("fees:voucher", pk=fee.pk)
    else:
        form = StudentFeeForm(instance=fee)

    context = {
        "form": form,
        "fee": fee,
        "title": f"Edit Fee Record: {fee.student.name} ({fee.get_fee_month_display()} {fee.fee_year})",
        "action_text": "Save Changes",
    }
    return render(request, "fees/form.html", context)


@admin_required
@require_POST
def fee_delete(request, pk):
    """Delete a fee payment record (missing records redirect with an error flash)."""
    try:
        fee = StudentFee.objects.select_related("student").get(pk=pk)
    except StudentFee.DoesNotExist:
        messages.error(
            request,
            f"Fee record #{pk} was not found. It may have already been deleted.",
        )
        return redirect("fees:list")
    student_name = fee.student.name
    month_display = fee.get_fee_month_display()
    year = fee.fee_year
    fee.delete()
    messages.success(
        request,
        f"Fee record for {student_name} ({month_display} {year}) has been deleted.",
    )
    return redirect("fees:list")


@admin_required
def fee_voucher(request, pk):
    """View and print official fee receipt voucher."""
    fee = get_object_or_404(
        StudentFee.objects.select_related(
            "student", "student__school_class", "recorded_by"
        ),
        pk=pk,
    )
    student = fee.student

    # Calculate student financial standing
    paid_fees = student.fees.filter(status=FeeStatus.PAID)
    total_paid_all_time = paid_fees.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    current_year_paid = (
        paid_fees.filter(fee_year=fee.fee_year).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    yearly_expected = student.yearly_fee
    yearly_pending = max(Decimal("0.00"), yearly_expected - current_year_paid)

    context = {
        "fee": fee,
        "student": student,
        "total_paid_all_time": total_paid_all_time,
        "current_year_paid": current_year_paid,
        "yearly_expected": yearly_expected,
        "yearly_pending": yearly_pending,
    }
    return render(request, "fees/voucher.html", context)


@admin_required
def api_student_fee_info(request, student_id):
    """Return JSON information regarding a student's fee rate and paid months for the given year."""
    student = get_object_or_404(
        Student.objects.select_related("school_class"), id=student_id
    )
    year = int(request.GET.get("year", timezone.now().year))

    paid_months = list(
        student.fees.filter(fee_year=year, status=FeeStatus.PAID).values_list(
            "fee_month", flat=True
        )
    )

    data = {
        "student_id": student.student_id,
        "name": student.name,
        "class_name": student.school_class.name,
        "effective_monthly_fee": float(student.effective_monthly_fee),
        "yearly_fee": float(student.yearly_fee),
        "paid_months": paid_months,
    }
    return JsonResponse(data)


def _defaulter_report_context(request):
    """Shared GET parsing + matrix building for the defaulter list views."""
    now = timezone.now()
    year_param = request.GET.get("year", "").strip()
    class_param = request.GET.get("class_id", "").strip()

    report_year = now.year
    if year_param.isdigit() and 2000 <= int(year_param) <= now.year + 1:
        report_year = int(year_param)

    selected_class = None
    if class_param.isdigit():
        selected_class = SchoolClass.objects.filter(pk=int(class_param)).first()

    students = Student.objects.filter(is_active=True).select_related("school_class")
    if selected_class:
        students = students.filter(school_class=selected_class)
    students = students.order_by("school_class__order", "school_class__id", "student_id")

    rows, summary = _build_defaulter_matrix(students, report_year)

    scope_label = selected_class.name if selected_class else "All Classes"
    classes = SchoolClass.objects.order_by("order", "id")
    available_years = list(range(now.year - 2, now.year + 2))

    month_headers = [
        {"num": num, "name": MONTHS_MAP[num][:3]} for num in range(1, 13)
    ]

    return {
        "rows": rows,
        "month_headers": month_headers,
        "report_year": report_year,
        "selected_class": selected_class,
        "scope_label": scope_label,
        "classes": classes,
        "available_years": available_years,
        **summary,
    }


@admin_required
def defaulter_list(request):
    """Class-wise fee defaulter matrix (Jan-Dec) for the academic year."""
    context = _defaulter_report_context(request)
    return render(request, "fees/defaulter_list.html", context)


@admin_required
def defaulter_list_print(request):
    """Print/PDF-ready A4 landscape version of the defaulter list report."""
    context = _defaulter_report_context(request)
    context["generated_at"] = timezone.now()
    return render(request, "fees/defaulter_list_print.html", context)
