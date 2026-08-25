from datetime import datetime
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.models import Attendance, AttendanceStatus
from apps.core.constants import MONTHS
from apps.fees.models import FeeStatus
from apps.students.models import Student
from apps.teachers.models import Teacher, TeacherAttendance, SalaryStatus

from .serializers import (
    AttendanceRecordSerializer,
    CustomTokenObtainPairSerializer,
    FeeRecordSerializer,
    StudentProfileSerializer,
)


def _get_student(request):
    """Retrieve active student profile linked to the request user, or None."""
    try:
        student = request.user.student_profile
        if student and student.is_active:
            return student
    except (Student.DoesNotExist, AttributeError):
        pass
    return None


def _get_teacher_profile(user):
    """Retrieve Teacher profile for an authenticated user, or return None.

    Uses ``getattr`` to avoid crashing with AttributeError when the reverse
    OneToOne relation is missing, and catches the related-object DoesNotExist
    exception raised by Django for unset OneToOne fields.
    """
    try:
        teacher = getattr(user, "teacher_profile", None)
        if teacher is not None and teacher.is_active:
            return teacher
    except Teacher.DoesNotExist:
        pass
    return None


@method_decorator(csrf_exempt, name='dispatch')
class StudentLoginView(APIView):
    """POST /api/v1/auth/login/
    Student authentication endpoint accepting Username or Student Registration ID.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {
                    "status": "success",
                    "message": "Login successful",
                    "payload": serializer.validated_data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "status": "error",
                "message": "Login failed",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


@method_decorator(csrf_exempt, name='dispatch')
class StudentProfileView(APIView):
    """GET /api/v1/students/profile/
    Returns full profile details of the logged-in student.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return Response(
                {
                    "status": "error",
                    "message": "Active student profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = StudentProfileSerializer(student, context={"request": request})
        return Response(
            {
                "status": "success",
                "message": "Student profile fetched successfully",
                "payload": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class StudentAttendanceView(APIView):
    """GET /api/v1/students/attendance/
    Returns attendance summary metrics and paginated records log.
    Supports filtering via query parameters: ?month=XX&year=YYYY
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return Response(
                {
                    "status": "error",
                    "message": "Active student profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        records = student.attendance_records.order_by("-date")
        total_days = records.count()
        present_count = records.filter(status=AttendanceStatus.PRESENT).count()
        absent_count = records.filter(status=AttendanceStatus.ABSENT).count()
        attendance_rate = round((present_count / total_days) * 100, 1) if total_days > 0 else 0.0

        # Optional filtering
        month_param = request.query_params.get("month", "").strip()
        year_param = request.query_params.get("year", "").strip()

        filtered_records = records
        if month_param.isdigit():
            filtered_records = filtered_records.filter(date__month=int(month_param))
        if year_param.isdigit():
            filtered_records = filtered_records.filter(date__year=int(year_param))

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page_results = paginator.paginate_queryset(filtered_records, request)
        serializer = AttendanceRecordSerializer(page_results, many=True, context={"request": request})

        payload = {
            "total_days": total_days,
            "present_count": present_count,
            "absent_count": absent_count,
            "attendance_rate": attendance_rate,
            "count": filtered_records.count(),
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data,
        }

        return Response(
            {
                "status": "success",
                "message": "Attendance records retrieved successfully",
                "payload": payload,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class StudentFeeView(APIView):
    """GET /api/v1/students/fees/
    Returns fee history, yearly pending balance, and payment status schedule.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        student = _get_student(request)
        if not student:
            return Response(
                {
                    "status": "error",
                    "message": "Active student profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        current_year = timezone.now().year
        fees = student.fees.order_by("-fee_year", "-fee_month", "-payment_date")
        paid_fees = fees.filter(status=FeeStatus.PAID)

        total_paid_fees = paid_fees.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
        curr_year_paid = paid_fees.filter(fee_year=current_year).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        yearly_expected = student.yearly_fee
        yearly_pending = max(Decimal("0.00"), yearly_expected - curr_year_paid)
        overall_status = "PAID" if yearly_pending == 0 else "PENDING"

        # 12-month schedule for current year
        paid_month_map = {f.fee_month: f for f in paid_fees.filter(fee_year=current_year)}
        months_schedule = []
        for m_num, m_name in MONTHS:
            fee_entry = paid_month_map.get(m_num)
            months_schedule.append({
                "month_num": m_num,
                "month_name": m_name,
                "is_paid": bool(fee_entry),
                "amount": str(fee_entry.amount) if fee_entry else str(student.effective_monthly_fee),
                "payment_date": fee_entry.payment_date.strftime("%Y-%m-%d") if fee_entry else None,
                "reference": fee_entry.reference if fee_entry else "",
            })

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page_results = paginator.paginate_queryset(fees, request)
        serializer = FeeRecordSerializer(page_results, many=True, context={"request": request})

        payload = {
            "effective_monthly_fee": str(student.effective_monthly_fee),
            "yearly_expected": str(yearly_expected),
            "curr_year_paid": str(curr_year_paid),
            "yearly_pending": str(yearly_pending),
            "total_paid_fees": str(total_paid_fees),
            "overall_status": overall_status,
            "months_schedule": months_schedule,
            "count": fees.count(),
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data,
        }

        return Response(
            {
                "status": "success",
                                "message": "Fee summary and history retrieved successfully",
                "payload": payload,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class TeacherAttendanceView(APIView):
    """GET/POST /api/v1/teacher/attendance/
    - GET:  List students of the teacher's assigned classes (with optional date).
    - POST: Save daily attendance for students.
    """
    permission_classes = [IsAuthenticated]

    def _get_assigned_class_ids(self, teacher):
        """Return assigned class ids for a teacher, tolerating unset relations."""
        if not teacher:
            return []
        primary_id = getattr(teacher, "assigned_class_id", None)
        if primary_id:
            return [primary_id]
        assigned_classes = getattr(teacher, "assigned_classes", None)
        if assigned_classes is None:
            return []
        return list(assigned_classes.values_list("id", flat=True))

    def get(self, request, *args, **kwargs):
        teacher = _get_teacher_profile(request.user)
        if not teacher:
            return Response(
                {
                    "status": "error",
                    "message": "Active teacher profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        assigned_class_ids = self._get_assigned_class_ids(teacher)
        if not assigned_class_ids:
            return Response(
                {"status": "success", "message": "No classes assigned", "payload": {"date": timezone.now().date().strftime("%Y-%m-%d"), "roster": []}},
                status=status.HTTP_200_OK,
            )
        date_str = request.GET.get("date", timezone.now().date().strftime("%Y-%m-%d"))
        class_id = request.GET.get("class_id")
        students = Student.objects.filter(
            school_class__in=assigned_class_ids, is_active=True
        ).order_by("student_id")
        if class_id and class_id.isdigit():
            students = students.filter(school_class_id=int(class_id))
        try:
            attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            attendance_date = timezone.now().date()
        existing = {
            att.student_id: att.status
            for att in Attendance.objects.filter(
                student__in=students, date=attendance_date
            )
        }
        roster = []
        for s in students:
            roster.append({
                "id": s.id,
                "student_id": s.student_id,
                "name": s.name,
                "date_of_birth": s.date_of_birth.strftime("%Y-%m-%d"),
                "gender_display": s.get_gender_display(),
                "school_class_name": s.school_class.name if s.school_class else "",
                "status": existing.get(s.id, AttendanceStatus.PRESENT),
            })
        return Response(
            {"status": "success", "message": "Attendance roster", "payload": {"date": attendance_date.strftime("%Y-%m-%d"), "roster": roster}},
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        teacher = _get_teacher_profile(request.user)
        if not teacher:
            return Response(
                {
                    "status": "error",
                    "message": "Active teacher profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        submissions = request.data.get("attendance", request.data.get("submissions", {}))
        date_str = request.data.get("date", timezone.now().date().strftime("%Y-%m-%d"))
        try:
            attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return Response(
                {"status": "error", "message": "Invalid date format."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        assigned_class_ids = self._get_assigned_class_ids(teacher)
        students = Student.objects.filter(
            school_class__in=assigned_class_ids, is_active=True
        ).order_by("student_id")
        marked_count = 0
        for student in students:
            status_val = submissions.get(str(student.id), AttendanceStatus.PRESENT)
            if status_val in [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT]:
                Attendance.objects.update_or_create(
                    student=student,
                    date=attendance_date,
                    defaults={"status": status_val, "marked_by": request.user},
                )
                marked_count += 1
        return Response(
            {
                "status": "success",
                "message": f"Attendance saved for {marked_count} student(s) on {attendance_date}.",
                                "payload": {"marked_count": marked_count, "date": attendance_date.strftime("%Y-%m-%d")},
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class TeacherSalaryView(APIView):
    """GET /api/v1/teacher/salary/ — base salary and monthly paid/pending breakdown."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        teacher = _get_teacher_profile(request.user)
        if not teacher:
            return Response(
                {
                    "status": "error",
                    "message": "Active teacher profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        current_year = timezone.now().year
        year = int(request.GET.get("year", current_year))
        paid_salaries = teacher.salaries.filter(
            salary_year=year, status=SalaryStatus.PAID
        ).order_by("-salary_month")
        paid_month_set = {s.salary_month for s in paid_salaries}
        monthly_statuses = []
        for m_num, m_name in MONTHS:
            salary_entry = next(
                (s for s in paid_salaries if s.salary_month == m_num), None
            )
            monthly_statuses.append({
                "month_num": m_num,
                "month_name": m_name,
                "amount": str(teacher.monthly_salary),
                "status": SalaryStatus.PAID if m_num in paid_month_set else SalaryStatus.PENDING,
                "payment_date": salary_entry.payment_date.strftime("%Y-%m-%d") if salary_entry else None,
            })
        payload = {
            "teacher_id": teacher.teacher_id,
            "name": teacher.name,
            "monthly_salary": str(teacher.monthly_salary),
            "yearly_salary": str(teacher.yearly_salary),
            "monthly_statuses": monthly_statuses,
        }
        return Response(
            {"status": "success", "message": "Teacher salary info", "payload": payload},
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class TeacherAttendanceScanView(APIView):
    """POST /api/v1/teacher/attendance/scan/   (alias: /api/v1/teachers/attendance/scan/)

    Body: {"token": "<QR payload scanned from the admin dashboard>"}

    Flow:
      1. Validate the HMAC-signed, date-bound QR token.
      2. Identify the teacher from the JWT auth header.
      3. If no attendance exists for today -> create one (Present + time_in).
         Otherwise respond idempotently with the original check-in time.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        from apps.attendance.qr_tokens import verify_token

        teacher = _get_teacher_profile(request.user)
        if not teacher:
            return Response(
                {
                    "status": "error",
                    "message": "Active teacher profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        token = (request.data.get("token") or "").strip()
        is_valid, reason = verify_token(token, timezone.localdate())
        if not is_valid:
            return Response(
                {"status": "error", "message": reason},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.localdate()
        existing = TeacherAttendance.objects.filter(teacher=teacher, date=today).first()
        if existing:
            check_in = (
                existing.time_in.strftime("%I:%M %p")
                if existing.time_in
                else "earlier today"
            )
            return Response(
                {
                    "status": "success",
                    "message": f"Attendance already marked at {check_in}.",
                    "payload": {
                        "duplicate": True,
                        "date": today.strftime("%Y-%m-%d"),
                        "time_in": existing.time_in.strftime("%H:%M:%S")
                        if existing.time_in
                        else None,
                    },
                },
                status=status.HTTP_200_OK,
            )

        now = timezone.localtime()
        record = TeacherAttendance.objects.create(
            teacher=teacher,
            date=today,
            time_in=now.time(),
            source="QR",
            recorded_by=request.user,
        )
        check_in_label = record.time_in.strftime("%I:%M %p")
        return Response(
            {
                "status": "success",
                "message": f"Attendance marked successfully at {check_in_label}",
                "payload": {
                    "duplicate": False,
                    "teacher_id": teacher.teacher_id,
                    "name": teacher.name,
                    "date": today.strftime("%Y-%m-%d"),
                    "time_in": record.time_in.strftime("%H:%M:%S"),
                },
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name='dispatch')
class TeacherLatestScanView(APIView):
    """GET /api/v1/teacher/attendance/latest-scan/
    (alias: /api/v1/teachers/attendance/latest-scan/)

    Lightweight polling feed for the admin dashboard QR widget. Returns the
    most recent QR check-in of the day plus live counters so the UI can
    refresh itself without a full page reload.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()

        todays_scans = (
            TeacherAttendance.objects.filter(date=today)
            .select_related("teacher")
            .order_by("-created_at", "-id")
        )
        latest = todays_scans.first()

        latest_payload = None
        if latest:
            latest_payload = {
                "id": latest.id,
                "teacher_id": latest.teacher.teacher_id,
                "name": latest.teacher.name,
                "status": latest.status,
                "source": latest.source,
                "time_in": latest.time_in.strftime("%H:%M:%S")
                if latest.time_in
                else None,
                "label": latest.time_in.strftime("%I:%M %p")
                if latest.time_in
                else "",
            }

        teacher_stats = {
            "present": todays_scans.filter(status="PRESENT").count(),
            "absent": todays_scans.filter(status="ABSENT").count(),
            "leave": todays_scans.filter(status="LEAVE").count(),
            "active_total": Teacher.objects.filter(is_active=True).count(),
        }

        # Refresh the student "Today's Attendance" tile alongside, since the
        # dashboard displays it next to the QR widget.
        student_records = Attendance.objects.filter(date=today)
        s_present = student_records.filter(status=AttendanceStatus.PRESENT).count()
        s_absent = student_records.filter(status=AttendanceStatus.ABSENT).count()
        s_total = s_present + s_absent
        s_rate = round((s_present / s_total) * 100, 1) if s_total else 0.0

        return Response(
            {
                "status": "success",
                "payload": {
                    "latest": latest_payload,
                    "teacher_stats": teacher_stats,
                    "student_today": {
                        "percentage": s_rate,
                        "present": s_present,
                        "absent": s_absent,
                        "marked": s_total,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
