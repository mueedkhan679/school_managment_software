import sys
from django.contrib.auth import get_user_model
from apps.teachers.models import Teacher

User = get_user_model()

try:
    teacher = Teacher.objects.get(teacher_id__iexact='tch-000002')
    user = teacher.user
    if not user:
        print("Teacher profile TCH-000002 has no linked User account.")
        sys.exit(1)
    
    print(f"Found Teacher: {teacher.name}")
    print(f"Associated Username: {user.username}")
    print(f"Is Active: {user.is_active}")
    
    if not user.is_active:
        print("Activating user...")
        user.is_active = True
    
    print("Setting password to 'zara12345'...")
    user.set_password('zara12345')
    user.save()
    
    print("----------------------------------------")
    print("Credentials successfully updated!")
    print(f"Username: {user.username} (or use teacher ID: {teacher.teacher_id})")
    print(f"Password: zara12345")
    print("----------------------------------------")
    
except Teacher.DoesNotExist:
    print("Teacher TCH-000002 does not exist in the database.")
except Exception as e:
    print(f"An error occurred: {e}")
