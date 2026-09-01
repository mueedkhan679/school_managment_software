from datetime import datetime, date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.core.constants import MONTHS
from apps.fees.models import FeeStatus
from apps.students.models import Student
from apps.teachers.models import (
    Teacher,
    TeacherAttendance,
    TeacherAttendanceStatus,
    SalaryStatus,
)

from .serializers import (
    AttendanceRecordSerializer,
    CustomTokenObtainPairSerializer,
    FeeRecordSerializer,
    StudentProfileSerializer,
)

User = get_user_model()


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
class TeacherClassListView(APIView):
    """GET /api/v1/teacher/classes/
    Returns ALL active school classes so any teacher can pick a class,
    view its enrolled students and take attendance for it.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from django.db.models import Count

        teacher = _get_teacher_profile(request.user)
        if not teacher:
            return Response(
                {
                    "status": "error",
                    "message": "Active teacher profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        classes = (
            SchoolClass.objects.annotate(
                active_student_count=Count(
                    "students", filter=models.Q(students__is_active=True)
                )
            )
            .order_by("order", "id")
        )

        payload = [
            {
                "id": c.id,
                "name": c.name,
                "student_count": c.active_student_count,
                # Keep the field name the Flutter model already parses.
                "monthly_fee": str(c.monthly_fee),
            }
            for c in classes
        ]
        return Response(
            {
                "status": "success",
                "message": "All active classes",
                "payload": {"classes": payload},
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class TeacherProfileApiView(APIView):
    """GET /api/v1/teacher/profile/
    Full profile of the logged-in teacher — powers the in-app Digital ID Card
    (photo, full name, teacher ID, designation, contact details) and any other
    profile surfaces in the mobile app.
    """
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

        photo_url = None
        if teacher.picture:
            try:
                photo_url = teacher.picture.url
            except ValueError:
                photo_url = None

        assigned_classes = [
            {"id": c.id, "name": c.name}
            for c in teacher.assigned_classes.all().order_by("order", "id")
        ]

        payload = {
            "teacher_id": teacher.teacher_id,
            "name": teacher.name,
            # The model has no dedicated designation column; every linked
            # account holds the TEACHER role so this is the canonical title.
            "designation": "Teacher",
            "phone": teacher.phone or "",
            "address": teacher.address or "",
            "cnic": teacher.cnic or "",
            "photo_url": photo_url,
            "date_joined": teacher.date_joined.strftime("%Y-%m-%d")
            if teacher.date_joined
            else None,
            "assigned_classes": assigned_classes,
            "primary_class_name": teacher.assigned_class.name
            if teacher.assigned_class
            else "",
        }
        return Response(
            {
                "status": "success",
                "message": "Teacher profile",
                "payload": payload,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class TeacherStudentCreateView(APIView):
    """POST /api/v1/teacher/students/add/
    Lets an authenticated teacher register a new student directly from the app.

    Accepts: full_name (or name), roll_number (unique within the class),
    classroom_id (or class_id), father_name, phone_number (optional),
    admission_date (defaults to today). ``date_of_birth``/``gender`` are not
    collected on this lightweight form, so they default to today / M.

    A Django ``User`` login account is provisioned automatically for every new
    student: username ``stu_<roll_number>`` (falling back to the permanent
    student_id when no roll number is supplied, with a numeric suffix added if
    the username is already taken) and default password ``Student@123``. The
    account is linked via ``Student.user`` and the credentials are returned in
    the 201 payload as ``username`` / ``default_password`` so the teacher can
    hand them to the student right away.
    """
    permission_classes = [IsAuthenticated]

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

        name = (request.data.get("full_name") or request.data.get("name") or "").strip()
        father_name = (request.data.get("father_name") or "").strip()
        roll_number = (request.data.get("roll_number") or "").strip()
        phone = (request.data.get("phone_number") or "").strip()
        class_id = request.data.get("classroom_id", request.data.get("class_id"))
        admission_date_str = request.data.get("admission_date") or ""

        # --- Required field validation ---
        if not name:
            return Response(
                {"status": "error", "message": "Student full name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not father_name:
            return Response(
                {"status": "error", "message": "Father name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not str(class_id or "").isdigit():
            return Response(
                {"status": "error", "message": "A valid classroom_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        school_class = SchoolClass.objects.filter(id=int(class_id)).first()
        if not school_class:
            return Response(
                {"status": "error", "message": "The selected class does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- admission date (defaults to today) ---
        admission_date = timezone.localdate()
        if admission_date_str:
            try:
                admission_date = datetime.strptime(admission_date_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return Response(
                    {"status": "error",
                     "message": "Invalid admission_date format (expected YYYY-MM-DD)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # --- roll number uniqueness within the class ---
        if roll_number and Student.objects.filter(
            school_class=school_class,
            roll_number__iexact=roll_number,
            is_active=True,
        ).exists():
            return Response(
                {"status": "error",
                 "message": f"A student with roll number '{roll_number}' already exists in this class."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- create the student + auto-provision a login account ---
        try:
            with transaction.atomic():
                student = Student.objects.create(
                    name=name,
                    father_name=father_name,
                    school_class=school_class,
                    roll_number=roll_number,
                    phone=phone,
                    date_of_birth=admission_date,
                    gender="M",
                    is_active=True,
                )
                # admission_date is auto_now_add so it must be set after creation
                # when the caller supplied a custom value.
                if admission_date_str:
                    student.admission_date = admission_date
                    student.save(update_fields=["admission_date"])

                # --- automatic User account creation ---
                # Username: stu_<roll_number> (or stu_<student_id> when no roll
                # number was supplied), uniquified with a suffix when taken.
                safe_roll = roll_number.strip().replace(" ", "_")
                base_username = (
                    f"stu_{safe_roll}" if safe_roll else f"stu_{student.student_id}"
                )
                username = base_username
                suffix = 2
                while User.objects.filter(username__iexact=username).exists():
                    username = f"{base_username}_{suffix}"
                    suffix += 1

                default_password = "Student@123"
                account = User.objects.create_user(
                    username=username,
                    password=default_password,
                    role=Role.STUDENT,
                    is_active=True,
                    first_name=name,
                    phone=phone,
                )
                student.user = account
                student.save(update_fields=["user"])
        except Exception:
            return Response(
                {"status": "error", "message": "Could not create the student. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "success",
                "message": "Student added successfully!",
                "payload": {
                    "id": student.id,
                    "student_id": student.student_id,
                    "name": student.name,
                    "roll_number": student.roll_number,
                    "father_name": student.father_name,
                    "class_id": school_class.id,
                    "class_name": school_class.name,
                    "phone": student.phone,
                    "admission_date": student.admission_date.strftime("%Y-%m-%d"),
                    # Login credentials for the auto-provisioned account
                    "username": account.username,
                    "default_password": default_password,
                },
                # Also duplicated at the top level so thin clients can read
                # them without digging into the payload.
                "username": account.username,
                "default_password": default_password,
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name='dispatch')
class TeacherAttendanceView(APIView):
    """GET/POST /api/v1/teacher/attendance/
    - GET:  List students from any class (optionally filtered by class_id & date).
    - POST: Save daily attendance for students in any class.
    """

    permission_classes = [IsAuthenticated]

    def _get_teacher_or_403(self, request):
        """Return active teacher profile or None (caller handles 403)."""
        return _get_teacher_profile(request.user)

    def get(self, request, *args, **kwargs):
        teacher = self._get_teacher_or_403(request)
        if not teacher:
            return Response(
                {
                    "status": "error",
                    "message": "Active teacher profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Allow teachers to view ALL active classes in the school
        all_classes = SchoolClass.objects.all()
        class_id = request.GET.get("class_id")

        # If class_id is specified, filter students to that class;
        # otherwise, when no class is selected, return all active students
        if class_id and class_id.isdigit():
            students = Student.objects.filter(
                school_class__id=int(class_id), is_active=True
            ).order_by("student_id")
        else:
            students = Student.objects.filter(
                is_active=True
            ).order_by("student_id")

        date_str = request.GET.get("date", timezone.now().date().strftime("%Y-%m-%d"))
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
                "school_class_id": s.school_class_id,
                "status": existing.get(s.id, AttendanceStatus.PRESENT),
                "is_marked": s.id in existing,
            })

        return Response(
            {"status": "success", "message": "Attendance roster",
             "payload": {"date": attendance_date.strftime("%Y-%m-%d"),
                          "classes": [{"id": c.id, "name": c.name} for c in all_classes],
                          "roster": roster}},
            status=status.HTTP_200_OK,
        )

    def post(self, request, *args, **kwargs):
        # ---------------------------------------------------------------
        # Every local is assigned here at the very top so that no matter
        # which code-path a request takes (early-return on 403, 400 on
        # bad date, empty roster, invalid status values, etc.) the names
        # referenced further down are always bound.  This eliminates the
        # ``UnboundLocalError`` (HTTP 500) that occurred when a variable
        # such as ``student``, ``status_val`` or ``response_data`` was
        # referenced before Python had a chance to bind it.
        # ---------------------------------------------------------------
        teacher = self._get_teacher_or_403(request)
        submissions = {}
        attendance_date = timezone.now().date()
        class_id = None
        students = Student.objects.none()
        marked_count = 0
        student = None
        status_val = AttendanceStatus.PRESENT
        obj = None
        created = False
        response_data = {}

        # --- Permission check -------------------------------------------------
        if not teacher:
            return Response(
                {
                    "status": "error",
                    "message": "Active teacher profile not found for this account.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # --- Parse submission payload -----------------------------------------
        # ``submissions`` may arrive as ``attendance`` or ``submissions``.
        # Guard against a non-dict value (e.g. ``None`` or a JSON list) so
        # that ``.get()`` below never raises ``AttributeError``.
        submissions = request.data.get("attendance", request.data.get("submissions", {}))
        if not isinstance(submissions, dict):
            submissions = {}

        # Default to the server's local today when ``date`` is missing or
        # blank.  Uses the stdlib ``date`` class directly so this line can
        # never be affected by a local rebinding of the ``timezone`` module
        # inside this method (the reported ``UnboundLocalError`` class).
        today_str = date.today().strftime("%Y-%m-%d")
        date_str = request.data.get("date") or today_str
        try:
            attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return Response(
                {"status": "error", "message": "Invalid date format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Resolve the roster of students to mark --------------------------
        # Allow teachers to mark attendance for ANY class, not just assigned ones
        class_id = request.data.get("class_id")
        if class_id and str(class_id).isdigit():
            students = Student.objects.filter(
                school_class__id=int(class_id), is_active=True
            ).order_by("student_id")
        else:
            students = Student.objects.filter(
                is_active=True
            ).order_by("student_id")

        # --- Save loop -------------------------------------------------------
        marked_count = 0
        for student in students:
            # Only students explicitly present in the payload are marked.
            # An empty/partial ``attendance`` map must never silently default
            # unlisted students to PRESENT — they are skipped instead.
            status_val = submissions.get(str(student.id))
            if status_val is None:
                continue
            if status_val in [
                AttendanceStatus.PRESENT,
                AttendanceStatus.ABSENT,
                AttendanceStatus.LEAVE,
            ]:
                # Restrict to once-per-day: ``update_or_create`` matching
                # (student, date) updates an existing row instead of creating
                # a duplicate or raising ``IntegrityError``.
                # ``marked_by`` stores the requesting user; the audit trail
                # resolves the Teacher profile via ``Attendance.marked_by_teacher``
                # so every record always tracks who took the attendance.
                obj, created = Attendance.objects.update_or_create(
                    student=student,
                    date=attendance_date,
                    defaults={"status": status_val, "marked_by": request.user},
                )

                # Auto-generate a parent/student notification every time a
                # record is successfully saved *or* updated — for PRESENT,
                # ABSENT and LEAVE statuses alike.
                try:
                    from apps.core.models import Notification

                    # Only students that have a linked login account can
                    # receive a notification (``Student.user`` is nullable).
                    if student.user:
                        Notification.objects.create(
                            user=student.user,
                            title="Attendance Update",
                            message=(
                                f"{student.name} was marked "
                                f"{str(status_val).upper()} on {attendance_date}."
                            ),
                        )
                except Exception:
                    # A notification-logging failure (e.g. DB hiccup on the
                    # Notification table) must never crash the core
                    # attendance-submission flow.
                    pass

                marked_count += 1

        # --- Build response --------------------------------------------------
        response_data = {
            "marked_count": marked_count,
            "date": attendance_date.strftime("%Y-%m-%d"),
            "marked_by_teacher_id": teacher.teacher_id,
        }

        return Response(
            {
                "status": "success",
                "message": f"Attendance saved for {marked_count} student(s) on {attendance_date}.",
                "payload": response_data,
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

        def _teacher_payload(record=None, duplicate=False):
            """Full teacher details surfaced on the scan confirmation screen."""
            return {
                "duplicate": duplicate,
                "teacher_id": teacher.teacher_id,
                "name": teacher.name,
                "phone": teacher.phone or "",
                "address": teacher.address or "",
                "photo_url": (
                    request.build_absolute_uri(teacher.picture.url)
                    if teacher.picture and hasattr(teacher.picture, "url")
                    else None
                ),
                "date": today.strftime("%Y-%m-%d"),
                "status": record.status if record else TeacherAttendanceStatus.PRESENT,
                "time_in": record.time_in.strftime("%H:%M:%S")
                if record and record.time_in
                else None,
                "time_in_label": record.time_in.strftime("%I:%M %p")
                if record and record.time_in
                else "",
            }

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
                    "message": f"Attendance Already Marked at {check_in}.",
                    "payload": _teacher_payload(existing, True),
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
        return Response(
            {
                "status": "success",
                "message": "Attendance Marked Successfully",
                "payload": _teacher_payload(record, False),
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


@method_decorator(csrf_exempt, name='dispatch')
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        if not old_password or not new_password:
            return Response({"status": "error", "message": "Both old and new passwords are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.check_password(old_password):
            return Response({"status": "error", "message": "Incorrect old password."}, status=status.HTTP_400_BAD_REQUEST)
            
        request.user.set_password(new_password)
        request.user.save()
        return Response({"status": "success", "message": "Password changed successfully."}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from apps.core.models import Notification
        notifications = Notification.objects.filter(user=request.user)
        payload = [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "created_at": n.created_at.isoformat()
            }
            for n in notifications
        ]
        # ``payload`` mirrors ``notifications`` so both consumers work:
        # the web dashboard reads ``notifications`` while the Flutter
        # student portal (NotificationCenterView) reads ``payload``.
        return Response(
            {"status": "success", "notifications": payload, "payload": payload},
            status=status.HTTP_200_OK
        )


@method_decorator(csrf_exempt, name='dispatch')
class NotificationClearView(APIView):
    permission_classes = [IsAuthenticated]

    def _clear_user_notifications(self, request):
        from apps.core.models import Notification
        count = Notification.objects.filter(user=request.user).count()
        Notification.objects.filter(user=request.user).delete()
        return Response(
            {
                "status": "success",
                "message": f"{count} notification(s) cleared successfully.",
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        return self._clear_user_notifications(request)

    def post(self, request, *args, **kwargs):
        return self._clear_user_notifications(request)
