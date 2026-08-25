# -*- coding: utf-8 -*-
"""Mark active teachers without an attendance entry today as Absent.

Run automatically at closing time, e.g.::

    python manage.py mark_auto_absent

or via a scheduler (Cron / Task Scheduler / Celery beat). After the configured
cut-off time, every active teacher who has NOT already been recorded as
Present or Leave for today is bulk-marked Absent with ``source = AUTO``.
Existing entries (Present, Leave, or a previous Absent) are never overwritten.
"""

from datetime import datetime as _dt

from django.core.management.base import BaseCommand

from apps.teachers.auto_absent import CUTOFF_HOUR, CUTOFF_MINUTE, mark_auto_absent


class Command(BaseCommand):
    help = "Mark active teachers with no attendance today as Absent (auto)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            default=None,
            help="Mark absent for this date (YYYY-MM-DD). Defaults to today.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run even if the current time is before the cutoff.",
        )

    def handle(self, *args, **options):
        target_date = None
        if options.get("date"):
            target_date = _dt.strptime(options["date"], "%Y-%m-%d").date()

        created = mark_auto_absent(target_date=target_date, force=options["force"])
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Marked {created} teacher(s) Absent (Auto-System)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "No change: either no active teachers are missing attendance, "
                    f"or the cut-off ({CUTOFF_HOUR:02d}:{CUTOFF_MINUTE:02d}) has not "
                    "passed (use --force to override)."
                )
            )