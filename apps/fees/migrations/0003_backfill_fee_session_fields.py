"""Backfill the session fields for fee records created before the columns
existed (school_class + session_year). Pre-existing rows get their class from
the paying student and a session string from fee_year."""

from django.db import migrations


def backfill_session_fields(apps, schema_editor):
    StudentFee = apps.get_model("fees", "StudentFee")
    for fee in StudentFee.objects.select_related("student").all():
        changed = False
        if fee.school_class_id is None and fee.student_id:
            fee.school_class_id = fee.student.school_class_id
            changed = True
        if not fee.session_year and fee.fee_year:
            fee.session_year = f"{fee.fee_year}-{fee.fee_year + 1}"
            changed = True
        if changed:
            fee.save(update_fields=["school_class", "session_year"])


class Migration(migrations.Migration):

    dependencies = [
        ("fees", "0002_studentfee_school_class_studentfee_session_year"),
    ]

    operations = [
        migrations.RunPython(backfill_session_fields, migrations.RunPython.noop),
    ]