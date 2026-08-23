from decimal import Decimal
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.core.constants import MONTHS
from apps.fees.models import FeeStatus, StudentFee
from apps.students.models import Student
from apps.teachers.models import Teacher

User = get_user_model()


class CustomTokenObtainPairSerializer(serializers.Serializer):
    """Custom serializer supporting login via Username OR Student Registration ID (e.g. STU-000001)."""

    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        login_input = attrs.get("username", "").strip()
        password = attrs.get("password", "")

        user = None

        # 1. Try direct authenticate by username
        user = authenticate(username=login_input, password=password)

        # 2. If not found, try lookup by student_id
        if not user:
            student = Student.objects.filter(student_id__iexact=login_input).first()
            if student and student.user:
                user = authenticate(username=student.user.username, password=password)

        # 3. If not found, try lookup by teacher_id
        if not user:
            teacher = Teacher.objects.filter(teacher_id__iexact=login_input).first()
            if teacher and teacher.user:
                user = authenticate(username=teacher.user.username, password=password)

        if not user:
            raise serializers.ValidationError({"detail": "Invalid credentials. Please check your ID/Username and password."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is disabled."})

        # Role-based profile validation
        if user.is_student:
            student_profile = getattr(user, "student_profile", None)
            if not student_profile or not student_profile.is_active:
                raise serializers.ValidationError({"detail": "No active student profile linked to this account."})
        elif user.is_teacher:
            teacher_profile = getattr(user, "teacher_profile", None)
            if not teacher_profile or not teacher_profile.is_active:
                raise serializers.ValidationError({"detail": "No active teacher profile linked to this account."})
        elif not user.is_admin:
            raise serializers.ValidationError({"detail": "This account is not authorized."})

        refresh = RefreshToken.for_user(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "student_id": getattr(user.student_profile, "student_id", "") if user.is_student else "",
                "student_name": getattr(user.student_profile, "name", "") if user.is_student else "",
                "teacher_id": getattr(user.teacher_profile, "teacher_id", "") if user.is_teacher else "",
                "teacher_name": getattr(user.teacher_profile, "name", "") if user.is_teacher else "",
            }
        }


class StudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for logged-in student profile details."""

    school_class_name = serializers.CharField(source="school_class.name", read_only=True)
    school_class_id = serializers.IntegerField(source="school_class.id", read_only=True)
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)
    effective_monthly_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    yearly_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    photo_url = serializers.SerializerMethodField()
    qr_code_data = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "student_id",
            "name",
            "father_name",
            "school_class_id",
            "school_class_name",
            "date_of_birth",
            "gender",
            "gender_display",
            "form_b_number",
            "email",
            "phone",
            "address",
            "photo_url",
            "admission_date",
            "custom_monthly_fee",
            "effective_monthly_fee",
            "yearly_fee",
            "qr_code_data",
        ]

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if obj.photo and hasattr(obj.photo, "url"):
            if request is not None:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

    def get_qr_code_data(self, obj):
        return f"STUDENT_ID:{obj.student_id}|NAME:{obj.name}|CLASS:{obj.school_class.name}"


class AttendanceRecordSerializer(serializers.ModelSerializer):
    """Serializer for individual attendance records."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    marked_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ["id", "date", "status", "status_display", "marked_by_name"]

    def get_marked_by_name(self, obj):
        return obj.marked_by.get_full_name() or obj.marked_by.username if obj.marked_by else "System"


class AttendanceSummarySerializer(serializers.Serializer):
    """Serializer for attendance dashboard and summary analytics."""

    total_days = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    attendance_rate = serializers.FloatField()
    records = AttendanceRecordSerializer(many=True)


class FeeRecordSerializer(serializers.ModelSerializer):
    """Serializer for fee history items."""

    fee_month_name = serializers.CharField(source="get_fee_month_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = StudentFee
        fields = [
            "id",
            "fee_month",
            "fee_month_name",
            "fee_year",
            "amount",
            "payment_date",
            "status",
            "status_display",
            "reference",
            "is_extra",
        ]


class FeeSummarySerializer(serializers.Serializer):
    """Serializer for student fee summary and financial status."""

    effective_monthly_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    yearly_expected = serializers.DecimalField(max_digits=12, decimal_places=2)
    curr_year_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    yearly_pending = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_paid_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    overall_status = serializers.CharField()
    monthly_schedule = serializers.ListField()
    history = FeeRecordSerializer(many=True)


# =============================================================================
# Teacher Portal Serializers
# =============================================================================

class TeacherClassSerializer(serializers.Serializer):
    """A single assigned class for the logged-in teacher."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class TeacherAttendanceStudentSerializer(serializers.Serializer):
    """A student roster entry for the teacher attendance interface."""

    id = serializers.IntegerField()
    student_id = serializers.CharField()
    name = serializers.CharField()
    date_of_birth = serializers.DateField(format="%Y-%m-%d")
    gender_display = serializers.CharField()
    school_class_name = serializers.CharField()
    status = serializers.CharField()


class TeacherSalaryMonthSerializer(serializers.Serializer):
    """A single month's salary status entry."""

    month_num = serializers.IntegerField()
    month_name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    payment_date = serializers.DateField(format="%Y-%m-%d")


class TeacherSalarySerializer(serializers.Serializer):
    """Teacher salary summary returned by GET /api/v1/teacher/salary/."""

    teacher_id = serializers.CharField()
    name = serializers.CharField()
    monthly_salary = serializers.DecimalField(max_digits=12, decimal_places=2)
    yearly_salary = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_statuses = TeacherSalaryMonthSerializer(many=True)
