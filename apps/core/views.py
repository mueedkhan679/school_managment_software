from decimal import Decimal

from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.decorators import admin_required
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.core.constants import MONTHS_MAP
from apps.fees.models import FeeStatus, StudentFee
from apps.students.models import Student
from apps.teachers.models import SalaryStatus, Teacher, TeacherSalary


def index(request):
    """Entry point: send visitors to login or to their role-based portal."""
    if request.user.is_authenticated:
        if request.user.is_teacher:
            return redirect("teacher_portal:dashboard")
        elif request.user.is_student:
            return redirect("student_portal:dashboard")
        return redirect("core:dashboard")
    return redirect("accounts:login")


@admin_required
def dashboard(request):
    """Admin dashboard with comprehensive school overview, financial indicators,
    filtered analytics (Year/Month), today's attendance summary, and class/student statistics.
    """
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    today = now.date()

    # Filter parameters
    year_param = request.GET.get("year", "").strip()
    month_param = request.GET.get("month", "").strip()

    selected_year = int(year_param) if year_param.isdigit() else None
    selected_month = int(month_param) if month_param.isdigit() and 1 <= int(month_param) <= 12 else None

    # Base QuerySets for fees and salaries
    fees_qs = StudentFee.objects.filter(status=FeeStatus.PAID)
    salaries_qs = TeacherSalary.objects.filter(status=SalaryStatus.PAID)
    attendance_qs = Attendance.objects.all()

    # Apply Year/Month filters
    filter_label = "All Time"
    if selected_year and selected_month:
        fees_qs = fees_qs.filter(fee_year=selected_year, fee_month=selected_month)
        salaries_qs = salaries_qs.filter(salary_year=selected_year, salary_month=selected_month)
        attendance_qs = attendance_qs.filter(date__year=selected_year, date__month=selected_month)
        month_name = MONTHS_MAP.get(selected_month, "")
        filter_label = f"{month_name} {selected_year}"
    elif selected_year:
        fees_qs = fees_qs.filter(fee_year=selected_year)
        salaries_qs = salaries_qs.filter(salary_year=selected_year)
        attendance_qs = attendance_qs.filter(date__year=selected_year)
        filter_label = f"Year {selected_year}"
    elif selected_month:
        fees_qs = fees_qs.filter(fee_month=selected_month)
        salaries_qs = salaries_qs.filter(salary_month=selected_month)
        attendance_qs = attendance_qs.filter(date__month=selected_month)
        month_name = MONTHS_MAP.get(selected_month, "")
        filter_label = f"All {month_name}s"

    # Main Filtered Financial Metrics
    total_income = fees_qs.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    total_expenses = salaries_qs.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    remaining_balance = total_income - total_expenses

    # Period Attendance Metrics
    period_marked_total = attendance_qs.count()
    period_present = attendance_qs.filter(status=AttendanceStatus.PRESENT).count()
    period_absent = attendance_qs.filter(status=AttendanceStatus.ABSENT).count()
    if period_marked_total > 0:
        period_attendance_rate = round((period_present / period_marked_total) * 100, 1)
    else:
        period_attendance_rate = 0.0

    # Counts
    total_students = Student.objects.filter(is_active=True).count()
    total_classes = SchoolClass.objects.count()
    total_teachers = Teacher.objects.filter(is_active=True).count()

    # All-time / Monthly / Yearly Reference Metrics
    all_time_income = StudentFee.objects.filter(status=FeeStatus.PAID).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    all_time_expenses = TeacherSalary.objects.filter(status=SalaryStatus.PAID).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
    all_time_balance = all_time_income - all_time_expenses

    monthly_fee_income = (
        StudentFee.objects.filter(
            fee_year=current_year,
            fee_month=current_month,
            status=FeeStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    monthly_teacher_salary = (
        TeacherSalary.objects.filter(
            salary_year=current_year,
            salary_month=current_month,
            status=SalaryStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    monthly_net_income = monthly_fee_income - monthly_teacher_salary

    yearly_fee_income = (
        StudentFee.objects.filter(
            fee_year=current_year,
            status=FeeStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    yearly_teacher_salary = (
        TeacherSalary.objects.filter(
            salary_year=current_year,
            status=SalaryStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    yearly_net_income = yearly_fee_income - yearly_teacher_salary

    # Attendance Overview for Today
    today_records = Attendance.objects.filter(date=today)
    today_marked_total = today_records.count()
    today_present = today_records.filter(status=AttendanceStatus.PRESENT).count()
    today_absent = today_records.filter(status=AttendanceStatus.ABSENT).count()
    if today_marked_total > 0:
        attendance_percentage = round((today_present / today_marked_total) * 100, 1)
    else:
        attendance_percentage = 0.0

    # Class statistics list
    classes_list = (
        SchoolClass.objects.annotate(
            active_students=models.Count(
                "students",
                filter=models.Q(students__is_active=True),
            )
        )
        .order_by("order", "id")
        .all()
    )

    # Admission Fees report widget (filterable by class)
    class_param = request.GET.get("class_id", "").strip()
    selected_class_id = int(class_param) if class_param.isdigit() else None

    admission_base = Student.objects.filter(
        is_active=True, admission_fee__isnull=False
    )
    if selected_class_id:
        admission_base = admission_base.filter(school_class_id=selected_class_id)

    admission_total = (
        admission_base.aggregate(total=models.Sum("admission_fee"))["total"]
        or Decimal("0.00")
    )
    admission_count = admission_base.count()

    admission_scope_label = "All Classes"
    if selected_class_id:
        matched_class = next(
            (c for c in classes_list if c.id == selected_class_id), None
        )
        admission_scope_label = (
            matched_class.name if matched_class else f"Class #{selected_class_id}"
        )

    admission_breakdown = (
        Student.objects.filter(is_active=True, admission_fee__isnull=False)
        .values("school_class__id", "school_class__name", "school_class__order")
        .annotate(total=models.Sum("admission_fee"), payments=models.Count("id"))
        .order_by("school_class__order", "school_class__id")
    )

    # Recent transactions
    recent_fees = StudentFee.objects.select_related(
        "student", "student__school_class"
    ).order_by("-payment_date", "-created_at")[:6]
    recent_salaries = TeacherSalary.objects.select_related("teacher").order_by(
        "-payment_date", "-created_at"
    )[:6]

    # Available years for filter dropdown (range around data + current_year)
    fee_years = list(StudentFee.objects.values_list("fee_year", flat=True).distinct())
    salary_years = list(TeacherSalary.objects.values_list("salary_year", flat=True).distinct())
    combined_years = set(fee_years + salary_years + [current_year, current_year - 1, current_year - 2])
    available_years = sorted(list(combined_years), reverse=True)

    context = {
        "current_year": current_year,
        "current_month": current_month,
        "current_month_name": MONTHS_MAP.get(current_month, ""),
        "today_date": today,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "filter_label": filter_label,
        "months_list": [(num, name) for num, name in MONTHS_MAP.items()],
        "available_years": available_years,
        # Simplified main financial metrics for filtered period
        "total_income": total_income,
        "total_expenses": total_expenses,
        "remaining_balance": remaining_balance,
        # Period attendance
        "period_marked_total": period_marked_total,
        "period_present": period_present,
        "period_absent": period_absent,
        "period_attendance_rate": period_attendance_rate,
        # Secondary tile counts
        "total_students": total_students,
        "total_classes": total_classes,
        "total_teachers": total_teachers,
        "today_marked_total": today_marked_total,
        "today_present": today_present,
        "today_absent": today_absent,
        "attendance_percentage": attendance_percentage,
        # All-time and monthly references
        "all_time_income": all_time_income,
        "all_time_expenses": all_time_expenses,
        "all_time_balance": all_time_balance,
        "total_fee_income": all_time_income,
        "total_teacher_salary": all_time_expenses,
        "current_balance": all_time_balance,
        "monthly_fee_income": monthly_fee_income,
        "yearly_fee_income": yearly_fee_income,
        "monthly_teacher_salary": monthly_teacher_salary,
        "yearly_teacher_salary": yearly_teacher_salary,
        "monthly_net_income": monthly_net_income,
        "yearly_net_income": yearly_net_income,
        # Lists
        "classes_list": classes_list,
        "recent_fees": recent_fees,
        "recent_salaries": recent_salaries,
        # Admission fees report widget
        "selected_class_id": selected_class_id,
        "admission_scope_label": admission_scope_label,
        "admission_total": admission_total,
        "admission_count": admission_count,
        "admission_breakdown": admission_breakdown,
    }
    return render(request, "core/dashboard.html", context)


@admin_required
def api_class_students(request, class_id):
    """Return JSON list of active students in a given class."""
    school_class = get_object_or_404(SchoolClass, id=class_id)
    students = school_class.students.filter(is_active=True).order_by("student_id")

    data = {
        "class_id": school_class.id,
        "class_name": school_class.name,
        "monthly_fee": float(school_class.monthly_fee),
        "total_students": students.count(),
        "students": [
            {
                "id": s.id,
                "student_id": s.student_id,
                "name": s.name,
                "father_name": s.father_name,
                "gender": s.get_gender_display(),
                "phone": s.phone or "—",
                "email": s.email or "—",
                "effective_monthly_fee": float(s.effective_monthly_fee),
                "photo_url": s.photo.url if s.photo else None,
            }
            for s in students
        ],
    }
    return JsonResponse(data)


@admin_required
def api_student_profile(request, student_id):
    """Return JSON details for a single student including fee & attendance stats."""
    if str(student_id).isdigit():
        student = get_object_or_404(
            Student.objects.select_related("school_class"), id=int(student_id)
        )
    else:
        student = get_object_or_404(
            Student.objects.select_related("school_class"), student_id=student_id
        )

    # Fee statistics
    paid_fees = student.fees.filter(status=FeeStatus.PAID).order_by(
        "-fee_year", "-fee_month", "-payment_date"
    )
    total_paid_fees = paid_fees.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

    current_year = timezone.now().year
    curr_year_paid = (
        paid_fees.filter(fee_year=current_year).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )
    yearly_expected = student.yearly_fee
    yearly_pending = max(Decimal("0.00"), yearly_expected - curr_year_paid)

    recent_fees_data = [
        {
            "id": f.id,
            "month_display": f.get_fee_month_display(),
            "fee_month": f.fee_month,
            "fee_year": f.fee_year,
            "amount": float(f.amount),
            "payment_date": f.payment_date.strftime("%Y-%m-%d"),
            "status": f.status,
            "reference": f.reference or "—",
            "is_extra": f.is_extra,
        }
        for f in paid_fees[:12]
    ]

    # Attendance statistics
    attendance_records = student.attendance_records.order_by("-date")
    total_attendance_days = attendance_records.count()
    present_count = attendance_records.filter(status=AttendanceStatus.PRESENT).count()
    absent_count = attendance_records.filter(status=AttendanceStatus.ABSENT).count()
    if total_attendance_days > 0:
        att_rate = round((present_count / total_attendance_days) * 100, 1)
    else:
        att_rate = 0.0

    recent_attendance_data = [
        {
            "date": a.date.strftime("%Y-%m-%d"),
            "status": a.status,
            "status_display": a.get_status_display(),
        }
        for a in attendance_records[:10]
    ]

    data = {
        "id": student.id,
        "student_id": student.student_id,
        "name": student.name,
        "father_name": student.father_name,
        "class_id": student.school_class.id,
        "class_name": student.school_class.name,
        "date_of_birth": student.date_of_birth.strftime("%Y-%m-%d"),
        "form_b_number": student.form_b_number or "—",
        "gender": student.get_gender_display(),
        "email": student.email or "—",
        "phone": student.phone or "—",
        "address": student.address or "—",
        "photo_url": student.photo.url if student.photo else None,
        "admission_date": student.admission_date.strftime("%Y-%m-%d"),
        "effective_monthly_fee": float(student.effective_monthly_fee),
        "yearly_expected_fee": float(yearly_expected),
        "total_paid_fees": float(total_paid_fees),
        "current_year_paid": float(curr_year_paid),
        "current_year_pending": float(yearly_pending),
        "recent_fees": recent_fees_data,
        "total_attendance_days": total_attendance_days,
        "present_count": present_count,
        "absent_count": absent_count,
        "attendance_percentage": att_rate,
        "recent_attendance": recent_attendance_data,
    }
    return JsonResponse(data)


def csrf_failure(request, reason=""):
    """Custom CSRF failure handler providing user-friendly 403 page."""
    context = {
        "reason": reason,
    }
    return render(request, "403.html", context, status=403)

