from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass
from apps.students.models import Gender, Student
from apps.teachers.models import Teacher

User = get_user_model()


class ClassroomManagementTestCase(TestCase):
    """Test suite for Phase 4 Class Management system."""

    def setUp(self):
        # Admin user
        self.admin = User.objects.create_user(
            username="admin_user",
            password="adminpassword123",
            role=Role.ADMIN,
        )

        # Non-admin user (teacher)
        self.teacher_user = User.objects.create_user(
            username="teacher_user",
            password="teacherpassword123",
            role=Role.TEACHER,
        )

        # Setup test classes
        self.cls1, _ = SchoolClass.objects.get_or_create(
            name="Class 1",
            defaults={"order": 1, "monthly_fee": Decimal("1500.00")},
        )
        self.cls1.order = 1
        self.cls1.monthly_fee = Decimal("1500.00")
        self.cls1.save()

        self.empty_class = SchoolClass.objects.create(
            name="Empty Class",
            order=99,
            monthly_fee=Decimal("2500.00"),
        )

        # Setup students in cls1
        self.stu1 = Student.objects.create(
            name="Hamza Tariq",
            father_name="Tariq Mahmood",
            school_class=self.cls1,
            date_of_birth=date(2015, 6, 15),
            gender=Gender.MALE,
            is_active=True,
        )
        self.stu2 = Student.objects.create(
            name="Ayesha Khan",
            father_name="Imran Khan",
            school_class=self.cls1,
            date_of_birth=date(2016, 1, 10),
            gender=Gender.FEMALE,
            custom_monthly_fee=Decimal("1200.00"),
            is_active=True,
        )
        self.stu_inactive = Student.objects.create(
            name="Bilal Asghar",
            father_name="Asghar Ali",
            school_class=self.cls1,
            date_of_birth=date(2014, 3, 20),
            gender=Gender.MALE,
            is_active=False,
        )

        # Setup teacher assigned to cls1
        self.teacher = Teacher.objects.create(
            name="Sir Ahmad",
            phone="03001234567",
            monthly_salary=Decimal("50000.00"),
            is_active=True,
        )
        self.teacher.assigned_classes.add(self.cls1)

    # ------------------ Access Control Tests ------------------

    def test_anonymous_redirected_from_all_views(self):
        """Unauthenticated requests to classroom views are redirected to login."""
        urls = [
            reverse("classrooms:list"),
            reverse("classrooms:create"),
            reverse("classrooms:detail", kwargs={"pk": self.cls1.pk}),
            reverse("classrooms:update", kwargs={"pk": self.cls1.pk}),
            reverse("classrooms:delete", kwargs={"pk": self.cls1.pk}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response.url)

    def test_non_admin_forbidden_from_all_views(self):
        """Non-admin users receive 403 Forbidden."""
        self.client.force_login(self.teacher_user)
        urls = [
            reverse("classrooms:list"),
            reverse("classrooms:detail", kwargs={"pk": self.cls1.pk}),
            reverse("classrooms:update", kwargs={"pk": self.cls1.pk}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    # ------------------ List View Tests ------------------

    def test_class_list_view_renders_correctly(self):
        """Class list page displays all classes with accurate student counts."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("classrooms:list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "classrooms/list.html")
        self.assertContains(response, "Class 1")
        self.assertContains(response, "Empty Class")
        self.assertContains(response, "Rs 1500.00")

        # Check annotated active student count
        classes = list(response.context["classes"])
        cls1_item = next(c for c in classes if c.pk == self.cls1.pk)
        self.assertEqual(cls1_item.active_students_count, 2)
        self.assertEqual(cls1_item.total_students_count, 3)

    # ------------------ Create View Tests ------------------

    def test_create_class_valid_data(self):
        """Admin can create a new class with valid inputs."""
        self.client.force_login(self.admin)
        post_data = {
            "name": "Grade 11 - Pre-Medical",
            "order": 13,
            "monthly_fee": "3500.00",
        }
        response = self.client.post(reverse("classrooms:create"), data=post_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("classrooms:list"))

        # Verify in database
        new_class = SchoolClass.objects.get(name="Grade 11 - Pre-Medical")
        self.assertEqual(new_class.order, 13)
        self.assertEqual(new_class.monthly_fee, Decimal("3500.00"))

    def test_create_class_invalid_data(self):
        """Creating a class with negative monthly fee fails validation."""
        self.client.force_login(self.admin)
        post_data = {
            "name": "Invalid Class",
            "order": 1,
            "monthly_fee": "-500.00",
        }
        response = self.client.post(reverse("classrooms:create"), data=post_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SchoolClass.objects.filter(name="Invalid Class").exists())

    def test_create_class_duplicate_name(self):
        """Duplicate class names are blocked by uniqueness validation."""
        self.client.force_login(self.admin)
        post_data = {
            "name": "Class 1",  # Already exists
            "order": 1,
            "monthly_fee": "2000.00",
        }
        response = self.client.post(reverse("classrooms:create"), data=post_data)
        self.assertEqual(response.status_code, 400)

    # ------------------ Detail View Tests ------------------

    def test_class_detail_view(self):
        """Class detail page renders class summary, assigned faculty, and enrolled students."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("classrooms:detail", kwargs={"pk": self.cls1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "classrooms/detail.html")
        self.assertContains(response, "Class 1")
        self.assertContains(response, "Hamza Tariq")
        self.assertContains(response, "Ayesha Khan")
        self.assertContains(response, "Sir Ahmad")
        self.assertEqual(response.context["active_count"], 2)
        self.assertEqual(response.context["total_count"], 3)

        # Expected monthly: stu1 (1500) + stu2 (1200) = 2700
        self.assertEqual(response.context["expected_monthly_income"], Decimal("2700.00"))
        self.assertEqual(response.context["expected_yearly_income"], Decimal("32400.00"))

    # ------------------ Update View Tests ------------------

    def test_class_update_get(self):
        """GET request on update view displays the pre-filled form."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("classrooms:update", kwargs={"pk": self.cls1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "classrooms/form.html")
        self.assertContains(response, "Class 1")

    def test_class_update_post_valid(self):
        """POST request with valid changes updates the class record."""
        self.client.force_login(self.admin)
        update_data = {
            "name": "Class 1 - Updated",
            "order": 2,
            "monthly_fee": "1800.00",
        }
        response = self.client.post(
            reverse("classrooms:update", kwargs={"pk": self.cls1.pk}),
            data=update_data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("classrooms:detail", kwargs={"pk": self.cls1.pk})
        )

        self.cls1.refresh_from_db()
        self.assertEqual(self.cls1.name, "Class 1 - Updated")
        self.assertEqual(self.cls1.order, 2)
        self.assertEqual(self.cls1.monthly_fee, Decimal("1800.00"))

    # ------------------ Delete View & Safety Tests ------------------

    def test_delete_class_with_enrolled_students_blocked(self):
        """Deleting a class with enrolled students is blocked to preserve data integrity."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("classrooms:delete", kwargs={"pk": self.cls1.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("classrooms:list"))

        # Confirm class was NOT deleted
        self.assertTrue(SchoolClass.objects.filter(pk=self.cls1.pk).exists())

    def test_delete_empty_class_succeeds(self):
        """Deleting an empty class without students succeeds."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("classrooms:delete", kwargs={"pk": self.empty_class.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("classrooms:list"))

        # Confirm class was deleted
        self.assertFalse(SchoolClass.objects.filter(pk=self.empty_class.pk).exists())
