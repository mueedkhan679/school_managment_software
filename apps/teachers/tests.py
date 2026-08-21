import io
from datetime import date
from decimal import Decimal
from PIL import Image

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.teachers.models import SalaryStatus, Teacher, TeacherSalary

User = get_user_model()


def create_test_image(filename="photo.jpg", size=(100, 100), color="purple"):
    """Helper to generate a valid in-memory image for upload testing."""
    file = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.save(file, "jpeg")
    file.seek(0)
    return SimpleUploadedFile(filename, file.read(), content_type="image/jpeg")


class TeacherManagementTestCase(TestCase):
    """Test suite for Phase 8 Teacher Management & Phase 9 Teacher Salary System."""

    def setUp(self):
        # Admin user
        self.admin = User.objects.create_user(
            username="admin_tch",
            password="adminpassword123",
            role=Role.ADMIN,
        )

        # Teacher user (non-admin)
        self.teacher_user = User.objects.create_user(
            username="faculty_user",
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

        # Setup teacher
        self.teacher = Teacher.objects.create(
            name="Prof. Usman Tariq",
            phone="03001234567",
            cnic="35201-1234567-1",
            monthly_salary=Decimal("50000.00"),
            address="Lahore, Pakistan",
            is_active=True,
        )
        self.teacher.assigned_classes.add(self.cls1, self.cls2)

        # Setup salary record for teacher
        self.salary = TeacherSalary.objects.create(
            teacher=self.teacher,
            salary_month=8,
            salary_year=2026,
            amount=Decimal("50000.00"),
            payment_date=date(2026, 8, 1),
            status=SalaryStatus.PAID,
            reference="SAL-202608-0001",
            recorded_by=self.admin,
        )

    # ------------------ Access Control Tests ------------------

    def test_anonymous_redirected_from_all_teacher_views(self):
        """Unauthenticated requests are redirected to login."""
        urls = [
            reverse("teachers:list"),
            reverse("teachers:create"),
            reverse("teachers:detail", kwargs={"teacher_id": self.teacher.teacher_id}),
            reverse("teachers:update", kwargs={"teacher_id": self.teacher.teacher_id}),
            reverse("teachers:delete", kwargs={"teacher_id": self.teacher.teacher_id}),
            reverse("teachers:salary_list"),
            reverse("teachers:salary_create"),
            reverse("teachers:salary_voucher", kwargs={"pk": self.salary.pk}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_forbidden_from_teacher_views(self):
        """Non-admin users receive 403 Forbidden."""
        self.client.force_login(self.teacher_user)
        urls = [
            reverse("teachers:list"),
            reverse("teachers:create"),
            reverse("teachers:detail", kwargs={"teacher_id": self.teacher.teacher_id}),
            reverse("teachers:salary_list"),
            reverse("teachers:salary_create"),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    # ------------------ Atomic Auto ID Generation Tests ------------------

    def test_atomic_teacher_id_generation_and_no_reuse(self):
        """Teacher IDs follow TCH-00000X format and never reuse IDs upon deletion."""
        t1 = Teacher.objects.create(
            name="Teacher A",
            phone="03001111111",
            monthly_salary=Decimal("30000.00"),
        )
        t2 = Teacher.objects.create(
            name="Teacher B",
            phone="03002222222",
            monthly_salary=Decimal("35000.00"),
        )

        self.assertTrue(t1.teacher_id.startswith("TCH-"))
        self.assertTrue(t2.teacher_id.startswith("TCH-"))
        self.assertNotEqual(t1.teacher_id, t2.teacher_id)

        # Deleting t2 must not cause the next teacher to reuse t2's ID
        t2_id_num = int(t2.teacher_id.split("-")[1])
        t2.delete()

        t3 = Teacher.objects.create(
            name="Teacher C",
            phone="03003333333",
            monthly_salary=Decimal("40000.00"),
        )
        t3_id_num = int(t3.teacher_id.split("-")[1])
        self.assertGreater(t3_id_num, t2_id_num)

    # ------------------ Teacher List, Search & Filter Tests ------------------

    def test_teacher_list_renders_correctly(self):
        """Teacher directory displays faculty with assigned classes and salary totals."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("teachers:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "teachers/list.html")
        self.assertContains(response, self.teacher.name)
        self.assertContains(response, self.teacher.teacher_id)
        self.assertContains(response, "Rs 50000.00")

    def test_teacher_search_and_class_filter(self):
        """Search query matches teacher ID, name, CNIC, or phone."""
        self.client.force_login(self.admin)

        # Search by name
        res = self.client.get(reverse("teachers:list") + "?q=Usman")
        self.assertContains(res, self.teacher.teacher_id)

        # Search by CNIC
        res = self.client.get(reverse("teachers:list") + "?q=35201-1234567")
        self.assertContains(res, self.teacher.name)

        # Filter by class
        res = self.client.get(reverse("teachers:list") + f"?class_id={self.cls1.id}")
        self.assertContains(res, self.teacher.name)

    # ------------------ Teacher Registration & Document Upload Tests ------------------

    def test_teacher_create_with_images_and_class_assignments(self):
        """Admin can register teacher with multiple assigned classes and CNIC uploads."""
        self.client.force_login(self.admin)
        photo = create_test_image("teacher.jpg")
        cnic_front = create_test_image("cnic_f.jpg")
        cnic_back = create_test_image("cnic_b.jpg")

        post_data = {
            "name": "Madam Fatima",
            "phone": "03219876543",
            "cnic": "35202-9876543-2",
            "monthly_salary": "45000.00",
            "address": "Model Town, Lahore",
            "assigned_classes": [self.cls1.id, self.cls2.id],
            "picture": photo,
            "cnic_front_pic": cnic_front,
            "cnic_back_pic": cnic_back,
        }
        response = self.client.post(reverse("teachers:create"), data=post_data)
        self.assertEqual(response.status_code, 302)

        new_tch = Teacher.objects.get(name="Madam Fatima")
        self.assertTrue(new_tch.teacher_id.startswith("TCH-"))
        self.assertEqual(new_tch.monthly_salary, Decimal("45000.00"))
        self.assertEqual(new_tch.yearly_salary, Decimal("540000.00"))
        self.assertEqual(new_tch.assigned_classes.count(), 2)
        self.assertTrue(bool(new_tch.picture))
        self.assertTrue(bool(new_tch.cnic_front_pic))

    def test_teacher_create_rejects_negative_salary(self):
        """Negative or zero monthly salary is blocked by form validation."""
        self.client.force_login(self.admin)
        post_data = {
            "name": "Invalid Teacher",
            "phone": "03001231231",
            "monthly_salary": "-1000.00",
        }
        response = self.client.post(reverse("teachers:create"), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())

    # ------------------ Teacher Profile & Soft Delete Tests ------------------

    def test_teacher_detail_view(self):
        """Teacher profile displays bio-data, assigned classes, and salary ledger."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("teachers:detail", kwargs={"teacher_id": self.teacher.teacher_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "teachers/detail.html")
        self.assertContains(response, self.teacher.name)
        self.assertContains(response, self.salary.reference)
        self.assertEqual(response.context["curr_year_paid"], Decimal("50000.00"))
        # Yearly expected = 50000 * 12 = 600000. Pending = 600000 - 50000 = 550000
        self.assertEqual(response.context["yearly_pending"], Decimal("550000.00"))

    def test_teacher_soft_delete_and_restore(self):
        """Soft-deleting teacher deactivates record; restore reactivates it."""
        self.client.force_login(self.admin)

        # Soft delete
        res = self.client.post(
            reverse("teachers:delete", kwargs={"teacher_id": self.teacher.teacher_id})
        )
        self.assertEqual(res.status_code, 302)
        self.teacher.refresh_from_db()
        self.assertFalse(self.teacher.is_active)

        # Restore
        res = self.client.post(
            reverse("teachers:restore", kwargs={"teacher_id": self.teacher.teacher_id})
        )
        self.assertEqual(res.status_code, 302)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.is_active)

    # ------------------ Phase 9: Salary Management Tests ------------------

    def test_salary_list_view(self):
        """Salary ledger displays disbursements and aggregated totals."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("teachers:salary_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "teachers/salary_list.html")
        self.assertContains(response, self.salary.reference)
        self.assertContains(response, self.teacher.name)
        self.assertEqual(response.context["month_total"], Decimal("50000.00"))

    def test_salary_create_success(self):
        """Admin can record a salary disbursement with auto-reference number."""
        self.client.force_login(self.admin)
        post_data = {
            "teacher": self.teacher.id,
            "salary_month": 9,
            "salary_year": 2026,
            "amount": "50000.00",
            "payment_date": "2026-09-01",
            "status": "PAID",
            "reference": "",  # Auto-generate
        }
        response = self.client.post(reverse("teachers:salary_create"), data=post_data)
        self.assertEqual(response.status_code, 302)

        new_sal = TeacherSalary.objects.get(
            teacher=self.teacher, salary_month=9, salary_year=2026
        )
        self.assertEqual(new_sal.amount, Decimal("50000.00"))
        self.assertEqual(new_sal.recorded_by, self.admin)
        self.assertTrue(new_sal.reference.startswith("SAL-202609-"))

    def test_salary_duplicate_protection(self):
        """Duplicate salary disbursement for same teacher + month + year is blocked."""
        self.client.force_login(self.admin)
        # August 2026 already recorded in setUp
        post_data = {
            "teacher": self.teacher.id,
            "salary_month": 8,
            "salary_year": 2026,
            "amount": "50000.00",
            "payment_date": "2026-08-15",
            "status": "PAID",
        }
        response = self.client.post(reverse("teachers:salary_create"), data=post_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("already been disbursed", str(response.context["form"].errors))

    def test_salary_voucher_view(self):
        """Official salary payslip voucher renders teacher details and remaining balance."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("teachers:salary_voucher", kwargs={"pk": self.salary.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "teachers/salary_voucher.html")
        self.assertContains(response, self.salary.reference)
        self.assertContains(response, self.teacher.name)
        self.assertEqual(response.context["yearly_pending"], Decimal("550000.00"))

    def test_api_teacher_salary_info(self):
        """API returns teacher monthly base salary and paid months list."""
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("teachers:api_teacher_salary_info", kwargs={"teacher_id": self.teacher.id}) + "?year=2026"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["teacher_id"], self.teacher.teacher_id)
        self.assertEqual(data["monthly_salary"], 50000.0)
        self.assertIn(8, data["paid_months"])
