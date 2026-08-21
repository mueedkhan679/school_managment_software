from decimal import Decimal
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import student_required
from apps.attendance.models import AttendanceStatus
from apps.core.constants import MONTHS
from apps.fees.models import FeeStatus
from apps.students.models import Student


def _get_student_profile(user):
    """Retrieve the Student profile for the logged-in user, raising 403 if unlinked."""
    try:
        student = user.student_profile
        if not student or not student.is_active:
            raise PermissionDenied("Active student profile not found.")
        return student
    except (Student.DoesNotExist, AttributeError):
        raise PermissionDenied("No student profile linked to this user account.")


@student_required
def student_dashboard(request):
    """Student portal personal dashboard displaying bio-data and quick overview."""
    student = _get_student_profile(request.user)

    current_year = timezone.now().year
    current_month = timezone.now().month

    # Quick fee status
    fees = student.fees.filter(status=FeeStatus.PAID)
    paid_this_month = fees.filter(fee_year=current_year, fee_month=current_month).exists()
    curr_year_paid = fees.filter(fee_year=current_year).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    yearly_pending = max(Decimal("0.00"), student.yearly_fee - curr_year_paid)

    # Quick attendance status
    attendance_records = student.attendance_records.all()
    total_days = attendance_records.count()
    present_count = attendance_records.filter(status=AttendanceStatus.PRESENT).count()
    absent_count = attendance_records.filter(status=AttendanceStatus.ABSENT).count()
    attendance_rate = round((present_count / total_days) * 100, 1) if total_days > 0 else 0.0

    context = {
        "student": student,
        "current_year": current_year,
        "paid_this_month": paid_this_month,
        "curr_year_paid": curr_year_paid,
        "yearly_pending": yearly_pending,
        "total_days": total_days,
        "present_count": present_count,
        "absent_count": absent_count,
        "attendance_rate": attendance_rate,
    }
    return render(request, "student_portal/dashboard.html", context)


@student_required
def student_fees(request):
    """Student portal fee summary page showing ledger and pending balance."""
    student = _get_student_profile(request.user)

    current_year = timezone.now().year
    fees = student.fees.order_by("-fee_year", "-fee_month", "-payment_date")
    paid_fees = fees.filter(status=FeeStatus.PAID)
    total_paid_fees = paid_fees.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    curr_year_paid = paid_fees.filter(fee_year=current_year).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    yearly_expected = student.yearly_fee
    yearly_pending = max(Decimal("0.00"), yearly_expected - curr_year_paid)

    # 12-month schedule for current year
    paid_month_map = {f.fee_month: f for f in paid_fees.filter(fee_year=current_year)}
    months_schedule = []
    for m_num, m_name in MONTHS:
        fee_entry = paid_month_map.get(m_num)
        months_schedule.append({
            "month_num": m_num,
            "month_name": m_name,
            "is_paid": bool(fee_entry),
            "fee": fee_entry,
        })

    # Pagination for fee ledger
    paginator = Paginator(fees, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "student": student,
        "current_year": current_year,
        "page_obj": page_obj,
        "months_schedule": months_schedule,
        "total_paid_fees": total_paid_fees,
        "curr_year_paid": curr_year_paid,
        "yearly_expected": yearly_expected,
        "yearly_pending": yearly_pending,
    }
    return render(request, "student_portal/fees.html", context)


@student_required
def student_attendance(request):
    """Student portal attendance summary page showing statistics and log calendar."""
    student = _get_student_profile(request.user)

    records = student.attendance_records.order_by("-date")
    total_days = records.count()
    present_count = records.filter(status=AttendanceStatus.PRESENT).count()
    absent_count = records.filter(status=AttendanceStatus.ABSENT).count()
    attendance_rate = round((present_count / total_days) * 100, 1) if total_days > 0 else 0.0

    # Filter by month/year if selected
    month_filter = request.GET.get("month", "").strip()
    year_filter = request.GET.get("year", "").strip()

    filtered_records = records
    if month_filter.isdigit():
        filtered_records = filtered_records.filter(date__month=int(month_filter))
    if year_filter.isdigit():
        filtered_records = filtered_records.filter(date__year=int(year_filter))

    paginator = Paginator(filtered_records, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "student": student,
        "total_days": total_days,
        "present_count": present_count,
        "absent_count": absent_count,
        "attendance_rate": attendance_rate,
        "months": MONTHS,
        "page_obj": page_obj,
        "selected_month": int(month_filter) if month_filter.isdigit() else None,
        "selected_year": int(year_filter) if year_filter.isdigit() else None,
    }
    return render(request, "student_portal/attendance.html", context)
