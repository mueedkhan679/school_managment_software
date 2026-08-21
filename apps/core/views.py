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

    today's attendance summary, and class/student statistics.
    """
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    today = now.date()

    # Counts
    total_students = Student.objects.filter(is_active=True).count()
    total_classes = SchoolClass.objects.count()
    total_teachers = Teacher.objects.filter(is_active=True).count()

    # Fee Income (Student fees with status PAID)
    monthly_fee_income = (
        StudentFee.objects.filter(
            fee_year=current_year,
            fee_month=current_month,
            status=FeeStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )

    yearly_fee_income = (
        StudentFee.objects.filter(
            fee_year=current_year,
            status=FeeStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )

    total_fee_income = (
        StudentFee.objects.filter(
            status=FeeStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # Teacher Salaries (status PAID)
    monthly_teacher_salary = (
        TeacherSalary.objects.filter(
            salary_year=current_year,
            salary_month=current_month,
            status=SalaryStatus.PAID,
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

    total_teacher_salary = (
        TeacherSalary.objects.filter(
            status=SalaryStatus.PAID,
        ).aggregate(total=models.Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # Net Income / Current Balance
    current_balance = total_fee_income - total_teacher_salary
    monthly_net_income = monthly_fee_income - monthly_teacher_salary
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

    # Recent transactions
    recent_fees = StudentFee.objects.select_related(
        "student", "student__school_class"
    ).order_by("-payment_date", "-created_at")[:6]
    recent_salaries = TeacherSalary.objects.select_related("teacher").order_by(
        "-payment_date", "-created_at"
    )[:6]

    context = {
        "current_year": current_year,
        "current_month": current_month,
        "current_month_name": MONTHS_MAP.get(current_month, ""),
        "today_date": today,
        "total_students": total_students,
        "total_classes": total_classes,
        "total_teachers": total_teachers,
        "monthly_fee_income": monthly_fee_income,
        "yearly_fee_income": yearly_fee_income,
        "total_fee_income": total_fee_income,
        "monthly_teacher_salary": monthly_teacher_salary,
        "yearly_teacher_salary": yearly_teacher_salary,
        "total_teacher_salary": total_teacher_salary,
        "current_balance": current_balance,
        "monthly_net_income": monthly_net_income,
        "yearly_net_income": yearly_net_income,
        "today_marked_total": today_marked_total,
        "today_present": today_present,
        "today_absent": today_absent,
        "attendance_percentage": attendance_percentage,
        "classes_list": classes_list,
        "recent_fees": recent_fees,
        "recent_salaries": recent_salaries,
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

