from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Role
from apps.classrooms.models import SchoolClass

from .models import Teacher
from .profile_utils import get_teacher_profile_for_user


User = get_user_model()


class TeacherProfileResolverTests(TestCase):
    def setUp(self):
        self.school_class = SchoolClass.objects.create(
            name="Resolver Class", order=1, monthly_fee=Decimal("1000.00")
        )

    def make_teacher(self, name):
        return Teacher.objects.create(
            name=name,
            phone="03001234567",
            monthly_salary=Decimal("30000.00"),
            assigned_class=self.school_class,
        )

    def test_links_unique_teacher_id_match(self):
        teacher = self.make_teacher("Unlinked Teacher")
        user = User.objects.create_user(
            username=teacher.teacher_id, password="password123", role=Role.TEACHER
        )

        self.assertEqual(get_teacher_profile_for_user(user), teacher)
        teacher.refresh_from_db()
        self.assertEqual(teacher.user_id, user.id)

    def test_links_unique_full_name_match(self):
        teacher = self.make_teacher("Amina Khan")
        user = User.objects.create_user(
            username="amina-khan", password="password123", role=Role.TEACHER
        )
        user.first_name = "Amina"
        user.last_name = "Khan"
        user.save(update_fields=["first_name", "last_name"])

        self.assertEqual(get_teacher_profile_for_user(user), teacher)

    def test_does_not_link_ambiguous_full_name_match(self):
        self.make_teacher("Same Name")
        self.make_teacher("Same Name")
        user = User.objects.create_user(
            username="same-name", password="password123", role=Role.TEACHER
        )
        user.first_name = "Same"
        user.last_name = "Name"
        user.save(update_fields=["first_name", "last_name"])

        self.assertIsNone(get_teacher_profile_for_user(user))
        self.assertEqual(Teacher.objects.filter(user__isnull=False).count(), 0)