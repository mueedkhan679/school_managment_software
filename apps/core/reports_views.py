from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.decorators import admin_required
from apps.classrooms.models import SchoolClass
from apps.core.constants import MONTHS, MONTHS_MAP
from apps.fees.models import FeeStatus, StudentFee
from apps.students.models import Student
from apps.teachers.models import SalaryStatus, Teacher, TeacherSalary


@admin_required
def financial_reports(request):
    """Comprehensive Financial Reporting & Analytics Dashboard."""
    now = timezone.now()
    today = now.date()
    current_year = now.year
    current_month = now.month

    # Get selected filters
    selected_year = int(request.GET.get("year", current_year))
    selected_month = int(request.GET.get("month", current_month))
    selected_class_id = request.GET.get("class_id", "").strip()
    selected_class_id = int(selected_class_id) if selected_class_id.isdigit() else None

    # Available filter options
    classes = SchoolClass.objects.order_by("order", "id")
    available_years = list(range(current_year - 3, current_year + 3))

    # Active students base queryset
    active_students_qs = Student.objects.filter(is_active=True).select_related("school_class")
    if selected_class_id:
        active_students_qs = active_students_qs.filter(school_class_id=selected_class_id)

    active_students_list = list(active_students_qs)
    total_active_students = len(active_students_list)

    # Core Calculations - Expected Tuition
    expected_monthly_billing = sum(
        (s.effective_monthly_fee for s in active_students_list), Decimal("0.00")
    )
    expected_yearly_billing = expected_monthly_billing * 12

    # Fee Income Queries
    base_fee_qs = StudentFee.objects.filter(status=FeeStatus.PAID)
    if selected_class_id:
        base_fee_qs = base_fee_qs.filter(student__school_class_id=selected_class_id)

    today_fee_collection = (
        StudentFee.objects.filter(payment_date=today, status=FeeStatus.PAID).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0.00")
    )

    selected_month_fee_collection = (
        base_fee_qs.filter(
            fee_year=selected_year,
            fee_month=selected_month,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    selected_year_fee_collection = (
        base_fee_qs.filter(
            fee_year=selected_year,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    all_time_fee_collection = (
        base_fee_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )

    # Pending Fees
    year_pending_fees = max(
        Decimal("0.00"), expected_yearly_billing - selected_year_fee_collection
    )
    month_pending_fees = max(
        Decimal("0.00"), expected_monthly_billing - selected_month_fee_collection
    )

    # Salary Expenses (School-wide)
    base_salary_qs = TeacherSalary.objects.filter(status=SalaryStatus.PAID)

    selected_month_salaries = (
        base_salary_qs.filter(
            salary_year=selected_year,
            salary_month=selected_month,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    selected_year_salaries = (
        base_salary_qs.filter(
            salary_year=selected_year,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    all_time_salaries = (
        base_salary_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )

    # Net Income / Balances
    month_net_income = selected_month_fee_collection - selected_month_salaries
    year_net_income = selected_year_fee_collection - selected_year_salaries
    all_time_net_balance = all_time_fee_collection - all_time_salaries

    # 1. Class-wise Breakdown Report
    class_reports = []
    classes_to_report = (
        [SchoolClass.objects.get(id=selected_class_id)]
        if selected_class_id
        else list(classes)
    )

    for sc in classes_to_report:
        c_students = [s for s in active_students_list if s.school_class_id == sc.id]
        c_student_count = len(c_students)
        c_expected_monthly = sum(
            (s.effective_monthly_fee for s in c_students), Decimal("0.00")
        )
        c_expected_yearly = c_expected_monthly * 12

        # Actual collections
        c_month_collected = (
            StudentFee.objects.filter(
                student__school_class=sc,
                fee_year=selected_year,
                fee_month=selected_month,
                status=FeeStatus.PAID,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        c_year_collected = (
            StudentFee.objects.filter(
                student__school_class=sc,
                fee_year=selected_year,
                status=FeeStatus.PAID,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        c_month_pending = max(Decimal("0.00"), c_expected_monthly - c_month_collected)
        c_year_pending = max(Decimal("0.00"), c_expected_yearly - c_year_collected)

        c_month_rate = (
            round((c_month_collected / c_expected_monthly) * 100, 1)
            if c_expected_monthly > 0
            else 0.0
        )
        c_year_rate = (
            round((c_year_collected / c_expected_yearly) * 100, 1)
            if c_expected_yearly > 0
            else 0.0
        )

        class_reports.append(
            {
                "class": sc,
                "student_count": c_student_count,
                "expected_monthly": c_expected_monthly,
                "collected_monthly": c_month_collected,
                "pending_monthly": c_month_pending,
                "month_rate": c_month_rate,
                "expected_yearly": c_expected_yearly,
                "collected_yearly": c_year_collected,
                "pending_yearly": c_year_pending,
                "year_rate": c_year_rate,
            }
        )

    # 2. Month-by-Month Annual Breakdown (Jan to Dec for selected_year)
    monthly_breakdown = []
    annual_total_income = Decimal("0.00")
    annual_total_salaries = Decimal("0.00")

    for m_num, m_name in MONTHS:
        m_income = (
            base_fee_qs.filter(
                fee_year=selected_year,
                fee_month=m_num,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        m_salaries = (
            base_salary_qs.filter(
                salary_year=selected_year,
                salary_month=m_num,
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        m_net = m_income - m_salaries
        annual_total_income += m_income
        annual_total_salaries += m_salaries

        monthly_breakdown.append(
            {
                "month_num": m_num,
                "month_name": m_name,
                "income": m_income,
                "salaries": m_salaries,
                "net": m_net,
                "is_profit": m_net >= 0,
            }
        )

    annual_net_profit_loss = annual_total_income - annual_total_salaries

    context = {
        "today_date": today,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "selected_month_name": MONTHS_MAP.get(selected_month, ""),
        "selected_class_id": selected_class_id,
        "classes": classes,
        "available_years": available_years,
        "months": MONTHS,
        "total_active_students": total_active_students,
        "today_fee_collection": today_fee_collection,
        "month_fee_collection": selected_month_fee_collection,
        "year_fee_collection": selected_year_fee_collection,
        "all_time_fee_collection": all_time_fee_collection,
        "expected_monthly_billing": expected_monthly_billing,
        "expected_yearly_billing": expected_yearly_billing,
        "month_pending_fees": month_pending_fees,
        "year_pending_fees": year_pending_fees,
        "month_salaries": selected_month_salaries,
        "year_salaries": selected_year_salaries,
        "all_time_salaries": all_time_salaries,
        "month_net_income": month_net_income,
        "year_net_income": year_net_income,
        "all_time_net_balance": all_time_net_balance,
        "class_reports": class_reports,
        "monthly_breakdown": monthly_breakdown,
        "annual_total_income": annual_total_income,
        "annual_total_salaries": annual_total_salaries,
        "annual_net_profit_loss": annual_net_profit_loss,
    }
    return render(request, "core/reports.html", context)
