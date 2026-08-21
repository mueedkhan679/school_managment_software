from datetime import datetime
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.decorators import teacher_required
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.students.models import Student
from apps.teachers.models import Teacher


def _get_teacher_profile(user):
    """Retrieve the Teacher profile for the logged-in user, raising 403 if unlinked."""
    try:
        teacher = user.teacher_profile
        if not teacher or not teacher.is_active:
            raise PermissionDenied("Active teacher profile not found.")
        return teacher
    except (Teacher.DoesNotExist, AttributeError):
        raise PermissionDenied("No teacher profile linked to this user account.")


@teacher_required
def teacher_dashboard(request):
    """Teacher portal home dashboard displaying assigned classes and summary stats."""
    teacher = _get_teacher_profile(request.user)
    assigned_classes = teacher.assigned_classes.all().order_by("order", "id")

    # Counts
    assigned_students_count = Student.objects.filter(
        school_class__in=assigned_classes, is_active=True
    ).count()

    today = timezone.now().date()
    today_records = Attendance.objects.filter(
        student__school_class__in=assigned_classes, date=today
    )
    today_marked_total = today_records.count()
    today_present = today_records.filter(status=AttendanceStatus.PRESENT).count()

    context = {
        "teacher": teacher,
        "assigned_classes": assigned_classes,
        "assigned_students_count": assigned_students_count,
        "today_date": today,
        "today_marked_total": today_marked_total,
        "today_present": today_present,
    }
    return render(request, "teacher_portal/dashboard.html", context)


@teacher_required
def teacher_mark_attendance(request):
    """Teacher portal attendance marking interface restricted strictly to assigned classes."""
    teacher = _get_teacher_profile(request.user)
    assigned_classes = teacher.assigned_classes.all().order_by("order", "id")
    today_str = timezone.now().date().strftime("%Y-%m-%d")

    if request.method == "POST":
        class_id = request.POST.get("class_id")
        date_str = request.POST.get("date", today_str)

        school_class = get_object_or_404(SchoolClass, id=class_id)
        # Strict access check: class must be assigned to this teacher
        if school_class not in assigned_classes:
            raise PermissionDenied("You are not assigned to this class.")

        try:
            attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("teacher_portal:mark")

        students = school_class.students.filter(is_active=True).order_by("student_id")
        marked_count = 0

        for student in students:
            status_val = request.POST.get(f"status_{student.id}")
            if status_val in [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT]:
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
            f"Attendance saved for {marked_count} student(s) of '{school_class.name}' on {attendance_date}.",
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
        target_class = get_object_or_404(SchoolClass, id=int(class_id))
        if target_class not in assigned_classes:
            raise PermissionDenied("You are not assigned to this class.")
        selected_class = target_class

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
        "teacher": teacher,
        "assigned_classes": assigned_classes,
        "selected_class": selected_class,
        "date_str": date_str,
        "selected_date": parsed_date,
        "roster": roster,
        "AttendanceStatus": AttendanceStatus,
    }
    return render(request, "teacher_portal/mark.html", context)


@teacher_required
def teacher_attendance_history(request):
    """Teacher portal attendance history viewer restricted strictly to assigned classes."""
    teacher = _get_teacher_profile(request.user)
    assigned_classes = teacher.assigned_classes.all().order_by("order", "id")

    records = Attendance.objects.filter(
        student__school_class__in=assigned_classes
    ).select_related("student", "student__school_class", "marked_by").order_by("-date", "student__student_id")

    # Filters
    class_filter = request.GET.get("class_id", "").strip()
    date_filter = request.GET.get("date", "").strip()

    if class_filter.isdigit():
        target_class_id = int(class_filter)
        if not assigned_classes.filter(id=target_class_id).exists():
            raise PermissionDenied("You are not assigned to this class.")
        records = records.filter(student__school_class_id=target_class_id)

    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            records = records.filter(date=parsed_date)
        except ValueError:
            pass

    # Pagination
    paginator = Paginator(records, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "teacher": teacher,
        "assigned_classes": assigned_classes,
        "page_obj": page_obj,
        "selected_class": int(class_filter) if class_filter.isdigit() else None,
        "selected_date": date_filter,
        "total_records": records.count(),
    }
    return render(request, "teacher_portal/history.html", context)
