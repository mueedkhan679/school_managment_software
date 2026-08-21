from datetime import datetime
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.decorators import admin_required
from apps.classrooms.models import SchoolClass
from apps.core.constants import MONTHS
from apps.students.models import Student
from .models import Attendance, AttendanceStatus

User = get_user_model()


def get_student_attendance_stats(student):
    """Return attendance summary dictionary for a single student."""
    records = student.attendance_records.all()
    total_days = records.count()
    present_count = records.filter(status=AttendanceStatus.PRESENT).count()
    absent_count = records.filter(status=AttendanceStatus.ABSENT).count()
    percentage = round((present_count / total_days) * 100, 1) if total_days > 0 else 0.0
    return {
        "total_days": total_days,
        "present_count": present_count,
        "absent_count": absent_count,
        "percentage": percentage,
    }


@admin_required
def admin_attendance_list(request):
    """Admin attendance record viewer with comprehensive filtering capabilities.

    Filters: Date, Month, Year, Class, Student (ID/name), and Teacher (marked_by).
    """
    records = Attendance.objects.select_related(
        "student", "student__school_class", "marked_by"
    ).order_by("-date", "student__student_id")

    # Filter parameters
    date_filter = request.GET.get("date", "").strip()
    month_filter = request.GET.get("month", "").strip()
    year_filter = request.GET.get("year", "").strip()
    class_filter = request.GET.get("class_id", "").strip()
    student_filter = request.GET.get("q", "").strip()
    marked_by_filter = request.GET.get("marked_by", "").strip()

    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            records = records.filter(date=parsed_date)
        except ValueError:
            pass

    if month_filter.isdigit():
        records = records.filter(date__month=int(month_filter))

    if year_filter.isdigit():
        records = records.filter(date__year=int(year_filter))

    if class_filter.isdigit():
        records = records.filter(student__school_class_id=int(class_filter))

    if student_filter:
        records = records.filter(
            models.Q(student__student_id__icontains=student_filter)
            | models.Q(student__name__icontains=student_filter)
        )

    if marked_by_filter.isdigit():
        records = records.filter(marked_by_id=int(marked_by_filter))

    # Aggregated metrics for current view
    total_count = records.count()
    present_count = records.filter(status=AttendanceStatus.PRESENT).count()
    absent_count = records.filter(status=AttendanceStatus.ABSENT).count()
    attendance_rate = round((present_count / total_count) * 100, 1) if total_count > 0 else 0.0

    # Options for select boxes
    classes = SchoolClass.objects.order_by("order", "id")
    teachers = User.objects.filter(marked_attendance__isnull=False).distinct()
    available_years = (
        Attendance.objects.dates("date", "year")
        .values_list("date__year", flat=True)
        .distinct()
    )
    if not available_years:
        available_years = [timezone.now().year]

    # Pagination
    paginator = Paginator(records, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "classes": classes,
        "teachers": teachers,
        "months": MONTHS,
        "available_years": sorted(set(available_years), reverse=True),
        "selected_date": date_filter,
        "selected_month": int(month_filter) if month_filter.isdigit() else None,
        "selected_year": int(year_filter) if year_filter.isdigit() else None,
        "selected_class": int(class_filter) if class_filter.isdigit() else None,
        "student_query": student_filter,
        "selected_marked_by": int(marked_by_filter) if marked_by_filter.isdigit() else None,
        "total_count": total_count,
        "present_count": present_count,
        "absent_count": absent_count,
        "attendance_rate": attendance_rate,
    }
    return render(request, "attendance/admin_attendance.html", context)


@admin_required
def admin_attendance_mark(request):
    """Admin daily attendance marking interface for a selected class & date."""
    classes = SchoolClass.objects.order_by("order", "id")
    today_str = timezone.now().date().strftime("%Y-%m-%d")

    if request.method == "POST":
        class_id = request.POST.get("class_id")
        date_str = request.POST.get("date", today_str)

        school_class = get_object_or_404(SchoolClass, id=class_id)
        try:
            attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("attendance:admin_attendance_mark")

        students = school_class.students.filter(is_active=True).order_by("student_id")
        marked_count = 0

        for student in students:
            status_val = request.POST.get(f"status_{student.id}")
            if status_val in [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT]:
                # Enforces unique constraint: updates if exists, creates if new
                Attendance.objects.update_or_create(
                    student=student,
                    date=attendance_date,
                    defaults={
                        "status": status_val,
                        "marked_by": request.user,
                    },
                )
                marked_count += 1

        messages.success(
            request,
            f"Attendance recorded for {marked_count} student(s) of '{school_class.name}' on {attendance_date}.",
        )
        return redirect(
            f"{request.path}?class_id={school_class.id}&date={attendance_date.strftime('%Y-%m-%d')}"
        )

    # GET request
    class_id = request.GET.get("class_id")
    date_str = request.GET.get("date", today_str)

    selected_class = None
    roster = []
    parsed_date = timezone.now().date()

    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            parsed_date = timezone.now().date()
            date_str = parsed_date.strftime("%Y-%m-%d")

    if class_id and class_id.isdigit():
        selected_class = get_object_or_404(SchoolClass, id=int(class_id))
        students = selected_class.students.filter(is_active=True).order_by("student_id")
        attendance_qs = Attendance.objects.filter(
            student__in=students, date=parsed_date
        )
        existing_attendance = {att.student_id: att.status for att in attendance_qs}
        for s in students:
            status_val = existing_attendance.get(s.student_id, AttendanceStatus.PRESENT)
            roster.append({
                "student": s,
                "status": status_val,
            })

    context = {
        "classes": classes,
        "selected_class": selected_class,
        "date_str": date_str,
        "selected_date": parsed_date,
        "roster": roster,
        "AttendanceStatus": AttendanceStatus,
    }
    return render(request, "attendance/mark_attendance.html", context)
