import io
from datetime import date
from decimal import Decimal
from PIL import Image

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.classrooms.models import SchoolClass
from apps.fees.models import FeeStatus, StudentFee
from apps.students.models import Gender, Student

User = get_user_model()


def create_test_image(filename="test.jpg", size=(100, 100), color="blue"):
    """Helper to generate a valid in-memory image for upload testing."""
    file = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.save(file, "jpeg")
    file.seek(0)
    return SimpleUploadedFile(filename, file.read(), content_type="image/jpeg")


class StudentManagementTestCase(TestCase):
    """Test suite for Phase 5 Student Management system."""

    def setUp(self):
        # Admin user
        self.admin = User.objects.create_user(
            username="admin_user",
            password="adminpassword123",
            role=Role.ADMIN,
        )

        # Teacher user (non-admin)
        self.teacher_user = User.objects.create_user(
            username="teacher_user",
            password="teacherpassword123",
            role=Role.TEACHER,
        )

        # Setup classes
        self.cls1, _ = SchoolClass.objects.get_or_create(
            name="Class 1",
            defaults={"order": 1, "monthly_fee": Decimal("1500.00")},
        )
        self.cls2, _ = SchoolClass.objects.get_or_create(
            name="Class 2",
            defaults={"order": 2, "monthly_fee": Decimal("2000.00")},
        )

        # Setup test student
        self.student = Student.objects.create(
            name="Ali Khan",
            father_name="Tariq Khan",
            school_class=self.cls1,
            date_of_birth=date(2015, 5, 12),
            gender=Gender.MALE,
            form_b_number="35201-1234567-1",
            phone="03001234567",
            email="ali@example.com",
            address="Street 1, Lahore",
            is_active=True,
        )

    # ------------------ Access Control Tests ------------------

    def test_anonymous_redirected_from_all_student_views(self):
        """Unauthenticated requests are redirected to login."""
        urls = [
            reverse("students:list"),
            reverse("students:create"),
            reverse("students:detail", kwargs={"student_id": self.student.student_id}),
            reverse("students:update", kwargs={"student_id": self.student.student_id}),
            reverse("students:delete", kwargs={"student_id": self.student.student_id}),
            reverse("students:restore", kwargs={"student_id": self.student.student_id}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_forbidden_from_student_views(self):
        """Non-admin users receive 403 Forbidden."""
        self.client.force_login(self.teacher_user)
        urls = [
            reverse("students:list"),
            reverse("students:create"),
            reverse("students:detail", kwargs={"student_id": self.student.student_id}),
            reverse("students:update", kwargs={"student_id": self.student.student_id}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    # ------------------ Atomic Auto ID Generation Tests ------------------

    def test_atomic_student_id_generation_and_no_reuse(self):
        """Student IDs follow STU-00000X sequence format and never reuse IDs upon deletion."""
        s1 = Student.objects.create(
            name="Student Alpha",
            father_name="Father Alpha",
            school_class=self.cls1,
            date_of_birth=date(2016, 1, 1),
            gender=Gender.MALE,
        )
        s2 = Student.objects.create(
            name="Student Beta",
            father_name="Father Beta",
            school_class=self.cls1,
            date_of_birth=date(2016, 2, 2),
            gender=Gender.FEMALE,
        )

        self.assertTrue(s1.student_id.startswith("STU-"))
        self.assertTrue(s2.student_id.startswith("STU-"))
        self.assertNotEqual(s1.student_id, s2.student_id)

        # Deleting s2 should not cause the next student to reuse s2's ID
        s2_id_num = int(s2.student_id.split("-")[1])
        s2.delete()

        s3 = Student.objects.create(
            name="Student Gamma",
            father_name="Father Gamma",
            school_class=self.cls1,
            date_of_birth=date(2016, 3, 3),
            gender=Gender.MALE,
        )
        s3_id_num = int(s3.student_id.split("-")[1])
        self.assertGreater(s3_id_num, s2_id_num)

    # ------------------ List, Search & Filter Tests ------------------

    def test_student_list_renders_correctly(self):
        """Student directory displays students with class and status badges."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("students:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/list.html")
        self.assertContains(response, self.student.name)
        self.assertContains(response, self.student.student_id)

    def test_student_search(self):
        """Search query matches student ID, name, father name, form-b, or phone."""
        self.client.force_login(self.admin)

        # Match by name
        res = self.client.get(reverse("students:list") + "?q=Ali")
        self.assertContains(res, self.student.student_id)

        # Match by ID
        res = self.client.get(reverse("students:list") + f"?q={self.student.student_id}")
        self.assertContains(res, self.student.name)

        # Match by Form-B
        res = self.client.get(reverse("students:list") + "?q=35201-1234567")
        self.assertContains(res, self.student.name)

        # Non-matching query
        res = self.client.get(reverse("students:list") + "?q=NonExistentPerson")
        self.assertContains(res, "No students found matching your criteria")

    def test_student_filter_by_class(self):
        """Filter by class returns only students in selected class."""
        stu_cls2 = Student.objects.create(
            name="Sara Ahmed",
            father_name="Ahmed Bilal",
            school_class=self.cls2,
            date_of_birth=date(2015, 8, 14),
            gender=Gender.FEMALE,
        )
        self.client.force_login(self.admin)

        res = self.client.get(reverse("students:list") + f"?class_id={self.cls2.id}")
        self.assertContains(res, stu_cls2.name)
        self.assertNotContains(res, self.student.name)

    # ------------------ Student Create & File Upload Tests ------------------

    def test_student_create_with_valid_image(self):
        """Admin can register student with all required fields and valid passport image."""
        self.client.force_login(self.admin)
        image = create_test_image("passport.jpg")

        post_data = {
            "name": "Zaid Malik",
            "father_name": "Malik Asif",
            "school_class": self.cls1.id,
            "date_of_birth": "2016-04-10",
            "gender": "M",
            "form_b_number": "35201-9988776-5",
            "phone": "03111223344",
            "email": "zaid@example.com",
            "address": "Gulberg, Lahore",
            "custom_monthly_fee": "1400.00",
            "photo": image,
        }
        response = self.client.post(reverse("students:create"), data=post_data)
        self.assertEqual(response.status_code, 302)

        new_stu = Student.objects.get(name="Zaid Malik")
        self.assertTrue(new_stu.student_id.startswith("STU-"))
        self.assertEqual(new_stu.custom_monthly_fee, Decimal("1400.00"))
        self.assertTrue(bool(new_stu.photo))

    def test_student_create_rejects_invalid_file_extension(self):
        """Uploading non-image files (e.g. .txt, .exe) is rejected by image validation."""
        self.client.force_login(self.admin)
        bad_file = SimpleUploadedFile("malicious.txt", b"some text content", content_type="text/plain")

        post_data = {
            "name": "Hassan Raza",
            "father_name": "Raza Ali",
            "school_class": self.cls1.id,
            "date_of_birth": "2016-04-10",
            "gender": "M",
            "photo": bad_file,
        }
        response = self.client.post(reverse("students:create"), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("photo", response.context["form"].errors)

    def test_student_create_rejects_oversized_image(self):
        """Uploading an image larger than 5MB is rejected."""
        self.client.force_login(self.admin)
        # Create a large image (> 5MB)
        large_data = b"x" * (6 * 1024 * 1024)
        large_file = SimpleUploadedFile("large.jpg", large_data, content_type="image/jpeg")

        post_data = {
            "name": "Oversized Student",
            "father_name": "Father Name",
            "school_class": self.cls1.id,
            "date_of_birth": "2016-04-10",
            "gender": "M",
            "photo": large_file,
        }
        response = self.client.post(reverse("students:create"), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("photo", response.context["form"].errors)

    # ------------------ Detail View Tests ------------------

    def test_student_detail_view_with_fees_and_attendance(self):
        """Student detail page renders profile, fees paid/pending, and attendance metrics."""
        # Add fee record
        StudentFee.objects.create(
            student=self.student,
            fee_month=8,
            fee_year=2026,
            amount=Decimal("1500.00"),
            payment_date=date(2026, 8, 5),
            status=FeeStatus.PAID,
            reference="REC-STU-1",
        )

        # Add attendance records (1 present, 1 absent = 50%)
        Attendance.objects.create(
            student=self.student,
            date=date(2026, 8, 1),
            status=AttendanceStatus.PRESENT,
        )
        Attendance.objects.create(
            student=self.student,
            date=date(2026, 8, 2),
            status=AttendanceStatus.ABSENT,
        )

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("students:detail", kwargs={"student_id": self.student.student_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/detail.html")
        self.assertContains(response, self.student.name)
        self.assertContains(response, "Rs 1500.00")
        self.assertEqual(response.context["attendance_rate"], 50.0)
        self.assertEqual(response.context["total_paid_fees"], Decimal("1500.00"))

    # ------------------ Update & Soft-Delete Tests ------------------

    def test_student_update(self):
        """Admin can update student details."""
        self.client.force_login(self.admin)
        update_data = {
            "name": "Ali Khan Updated",
            "father_name": "Tariq Khan",
            "school_class": self.cls2.id,
            "date_of_birth": "2015-05-12",
            "gender": "M",
            "phone": "03009999999",
        }
        response = self.client.post(
            reverse("students:update", kwargs={"student_id": self.student.student_id}),
            data=update_data,
        )
        self.assertEqual(response.status_code, 302)

        self.student.refresh_from_db()
        self.assertEqual(self.student.name, "Ali Khan Updated")
        self.assertEqual(self.student.school_class, self.cls2)
        self.assertEqual(self.student.phone, "03009999999")

    def test_student_soft_delete_and_restore(self):
        """Deleting a student sets is_active=False without losing records; restore sets is_active=True."""
        self.client.force_login(self.admin)

        # Soft delete
        res = self.client.post(
            reverse("students:delete", kwargs={"student_id": self.student.student_id})
        )
        self.assertEqual(res.status_code, 302)

        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        # Verify row still exists in DB
        self.assertTrue(Student.objects.filter(student_id=self.student.student_id).exists())

        # Restore
        res = self.client.post(
            reverse("students:restore", kwargs={"student_id": self.student.student_id})
        )
        self.assertEqual(res.status_code, 302)

        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)


class AdmissionFeeTests(TestCase):
    """Optional Admission Fee field during registration + persistence/tracking."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_user",
            password="adminpassword123",
            role=Role.ADMIN,
        )
        self.cls1, _ = SchoolClass.objects.get_or_create(
            name="Class 1",
            defaults={"order": 1, "monthly_fee": Decimal("1500.00")},
        )

    def _payload(self, **overrides):
        data = {
            "name": "Hassan Raza",
            "father_name": "Raza Ali",
            "school_class": self.cls1.id,
            "date_of_birth": "2016-01-15",
            "gender": "M",
        }
        data.update(overrides)
        return data

    def test_registration_form_includes_admission_fee_field(self):
        """The registration form renders the optional Admission Fee input."""
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("students:create"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'name="admission_fee"')
        self.assertContains(resp, "Admission Fee")

    def test_create_with_admission_fee_records_amount_on_student(self):
        """Entering an admission fee tracks it as a payment on the student."""
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("students:create"),
            data=self._payload(admission_fee="5000.00"),
        )
        self.assertEqual(resp.status_code, 302)
        student = Student.objects.get(name="Hassan Raza")
        self.assertEqual(student.admission_fee, Decimal("5000.00"))

    def test_admission_fee_is_optional_defaults_to_none(self):
        """Leaving the field blank registers the student with no admission fee."""
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("students:create"), data=self._payload())
        self.assertEqual(resp.status_code, 302)
        student = Student.objects.get(name="Hassan Raza")
        self.assertIsNone(student.admission_fee)

    def test_negative_admission_fee_rejected(self):
        """Negative amounts are blocked by validation; no student is created."""
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("students:create"),
            data=self._payload(admission_fee="-100.00"),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("admission_fee", resp.context["form"].errors)
        self.assertFalse(Student.objects.filter(name="Hassan Raza").exists())

    # ------------------ Student Profile Display ------------------

    def _create_student_with_fee(self, amount):
        return Student.objects.create(
            name="Profile Kid",
            father_name="Fee Checker",
            school_class=self.cls1,
            date_of_birth=date(2015, 3, 3),
            gender=Gender.MALE,
            is_active=True,
            admission_fee=amount,
        )

    def test_detail_page_shows_recorded_admission_fee(self):
        """Web profile shows the amount when an admission fee exists."""
        student = self._create_student_with_fee(Decimal("5000.00"))
        self.client.force_login(self.admin)
        resp = self.client.get(
            reverse("students:detail", kwargs={"student_id": student.student_id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Admission Fee")
        self.assertContains(resp, "Rs 5000.00")

    def test_detail_page_shows_na_when_admission_fee_waived(self):
        """Web profile shows N/A / Free-Waived when no fee is set."""
        student = self._create_student_with_fee(None)
        self.client.force_login(self.admin)
        resp = self.client.get(
            reverse("students:detail", kwargs={"student_id": student.student_id})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Free / Waived")
        self.assertContains(resp, "N/A")
