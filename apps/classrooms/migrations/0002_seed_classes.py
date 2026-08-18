from django.db import migrations

# Class catalog in display order (Playgroup -> Class 12)
CLASSES = [
    ("Playgroup", 1),
    ("Nursery", 2),
    ("KG", 3),
    ("Class 1", 4),
    ("Class 2", 5),
    ("Class 3", 6),
    ("Class 4", 7),
    ("Class 5", 8),
    ("Class 6", 9),
    ("Class 7", 10),
    ("Class 8", 11),
    ("Class 9", 12),
    ("Class 10", 13),
    ("Class 11", 14),
    ("Class 12", 15),
]


def seed_classes(apps, schema_editor):
    SchoolClass = apps.get_model("classrooms", "SchoolClass")
    for name, order in CLASSES:
        SchoolClass.objects.get_or_create(name=name, defaults={"order": order})


def unseed_classes(apps, schema_editor):
    SchoolClass = apps.get_model("classrooms", "SchoolClass")
    SchoolClass.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("classrooms", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_classes, unseed_classes),
    ]
