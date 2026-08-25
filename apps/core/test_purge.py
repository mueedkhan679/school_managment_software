from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.students.models import Student
from apps.classrooms.models import SchoolClass

User = get_user_model()

class PurgeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser("admin", "admin@example.com", "adminpass")
        self.student_user = User.objects.create_user("student1", "student@example.com", "stu")
        self.student_user.role = "STUDENT"
        self.student_user.save()

    def test_non_admin_cannot_access_purge(self):
        self.client.login(username="student1", password="stu")
        response = self.client.post(reverse("core:system_reset"), {"password": "stu", "reset_scope": "ALL"})
        # admin_required decorator should redirect to login or dashboard, or return 403
        self.assertNotEqual(response.status_code, 200)

    def test_admin_wrong_password(self):
        self.client.login(username="admin", password="adminpass")
        response = self.client.post(reverse("core:system_reset"), {"password": "wrong", "reset_scope": "ALL"})
        self.assertRedirects(response, reverse("accounts:change_credentials"))
        
    def test_factory_reset_cascade(self):
        self.client.login(username="admin", password="adminpass")
        cls = SchoolClass.objects.create(name="Class 1", monthly_fee=100)
        Student.objects.create(name="S1", father_name="F1", school_class=cls, date_of_birth="2010-01-01", gender="M")
        
        response = self.client.post(reverse("core:system_reset"), {"password": "adminpass", "reset_scope": "ALL"})
        self.assertRedirects(response, reverse("accounts:change_credentials"))
        self.assertEqual(Student.objects.count(), 0)
        self.assertEqual(SchoolClass.objects.count(), 0)
