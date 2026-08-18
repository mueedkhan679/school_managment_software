from django.contrib.auth.hashers import make_password
from django.db import migrations


def seed_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    if not User.objects.filter(username="admin").exists():
        User.objects.create(
            username="admin",
            password=make_password("admin123"),  # PBKDF2-hashed, never plain text
            role="ADMIN",
            is_staff=True,
            is_superuser=True,
            is_active=True,
            first_name="School",
            last_name="Administrator",
        )


def unseed_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(username="admin").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_admin, unseed_admin),
    ]
