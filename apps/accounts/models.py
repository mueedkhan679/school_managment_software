from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    TEACHER = "TEACHER", "Teacher"
    STUDENT = "STUDENT", "Student"


class User(AbstractUser):
    """Custom user model supporting role-based access for admins, teachers and students.

    Passwords are always hashed by Django (PBKDF2 by default) - never stored in
    plain text. The ``role`` field drives role-based permissions across the system.
    """

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.ADMIN)
    phone = models.CharField(max_length=20, blank=True, verbose_name="Phone")

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_teacher(self) -> bool:
        return self.role == Role.TEACHER

    @property
    def is_student(self) -> bool:
        return self.role == Role.STUDENT

