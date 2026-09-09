"""Fee-clearance diagnostic tool.

Usage (from the project root):
    py fee_clearance_diag.py --list            # one-line summary for every student
    py fee_clearance_diag.py STU-000001        # full breakdown for one student ID

Prints, for the given student:
  1. current_session and school_class (the two values the tracker is keyed on)
  2. every PAID, is_extra=False StudentFee row with month / year / class / session
  3. a field-by-field mismatch analysis explaining exactly why is_fee_cleared
     is False (class mismatch, session mismatch, duplicate months, missing
     months, or non-PAID/extra rows).
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.fees.models import FeeStatus, StudentFee  # noqa: E402
from apps.students.models import MONTHS_PER_SESSION, Student  # noqa: E402

MONTH_NAMES = dict(StudentFee._meta.get_field("fee_month").choices)
RULE = "=" * 100


def fmt_class(fee_row):
    """Label for the class stored on a fee row (may be NULL/None)."""
    if fee_row.school_class_id is None:
        return "<NULL>"
    return f"{fee_row.school_class} (pk={fee_row.school_class_id})"


def dump_student(student):
    sc_id = student.school_class_id
    current_session = student.current_session
    paid_months_count = student.paid_months_count

    print(RULE)
    print(f"STUDENT           : {student.name} ({student.student_id})   is_active={student.is_active}")
    print(f"  1) school_class   : {student.school_class} (pk={sc_id})")
    print(f"     current_session: '{current_session}'")
    print(f"     MONTHS_PER_SESSION = {MONTHS_PER_SESSION}")

    all_fees = student.fees.all().order_by("fee_year", "fee_month", "id")
    print(f"\n  2) StudentFee rows for this student: {all_fees.count()} total "
          f"(status/extra filters NOT applied to this listing)")

    print("\n     #  month            year  status    extra  amount      "
          "school_class on row               session_year on row   counts?")
    print("     " + "-" * 95)

    counting_months = []          # months that pass every filter
    excluded = {"class": [], "session": [], "status_extra": []}

    for idx, f in enumerate(all_fees, start=1):
        class_ok = f.school_class_id == sc_id
        session_ok = (f.session_year == current_session) or (f.session_year == "")
        status_ok = (f.status == FeeStatus.PAID) and (not f.is_extra)
        counts = class_ok and session_ok and status_ok

        why = "YES"
        if not counts:
            reasons = []
            if not class_ok:
                reasons.append(f"class!={student.school_class.name}")
                excluded["class"].append(f)
            if not session_ok:
                reasons.append(f"session='{f.session_year}'!='{current_session}'")
                excluded["session"].append(f)
            if not status_ok:
                reasons.append(f"status={f.status}" + (" /EXTRA" if f.is_extra else ""))
                excluded["status_extra"].append(f)
            why = "no (" + "; ".join(reasons) + ")"

        if counts:
            counting_months.append(f.fee_month)

        session_label = f.session_year or "<BLANK>"
        session_disp = "'" + session_label + "'"
        class_disp = fmt_class(f)
        month_disp = str(MONTH_NAMES.get(f.fee_month, f.fee_month))
        status_disp = f.status or "-"
        print(
            f"     {idx:<2} {month_disp:<15} "
            f"{f.fee_year:<5} {status_disp:<9} {str(f.is_extra):<6} "
            f"Rs {f.amount:>9}  {class_disp:<32} "
            f"{session_disp:<24} {why}"
        )

    # -- 3) tally ----------------------------------------------------------
    distinct = sorted(set(counting_months))
    duplicates = sorted({m for m in counting_months if counting_months.count(m) > 1})
    missing = sorted(set(range(1, MONTHS_PER_SESSION + 1)) - set(distinct))

    print(f"\n  3) Tracker tally for class pk={sc_id} + session '{current_session}':")
    print(f"     rows counted                 : {len(counting_months)}")
    print(f"     DISTINCT months counted      : {len(distinct)}  -> {distinct}")
    if duplicates:
        print(f"     duplicate months (counted 1x): {duplicates}")
    print(f"     MISSING months (1..12)       : {missing or 'none'}")

    print(f"\n     excluded by school_class mismatch : {len(excluded['class'])}")
    print(f"     excluded by session_year mismatch : {len(excluded['session'])}")
    print(f"     excluded by status/is_extra       : {len(excluded['status_extra'])}")

    print(f"\n  4) RESULT: paid_months_count = {paid_months_count} "
          f"-> is_fee_cleared = {paid_months_count >= MONTHS_PER_SESSION}")

    # -- 5) diagnosis ------------------------------------------------------
    print("\n  5) DIAGNOSIS (exact reason is_fee_cleared is False):")
    reasons = []
    if excluded["class"]:
        by_class = {}
        for f in excluded["class"]:
            by_class[fmt_class(f)] = by_class.get(fmt_class(f), 0) + 1
        reasons.append(
            f"school_class mismatch: {len(excluded['class'])} PAID standard row(s) carry a "
            f"different/NULL class than the student's current class {student.school_class} "
            f"(pk={sc_id}): " + ", ".join(f"{k} x{v}" for k, v in by_class.items()) +
            f"  -> FIX: set school_class_id={sc_id} on those StudentFee rows."
        )
    if excluded["session"]:
        by_sess = {}
        for f in excluded["session"]:
            by_sess[f.session_year or "<BLANK>"] = by_sess.get(f.session_year or "<BLANK>", 0) + 1
        reasons.append(
            f"session_year mismatch: {len(excluded['session'])} PAID standard row(s) in the "
            f"current class carry session_year {sorted(by_sess)} while "
            f"current_session='{current_session}'. Only rows with session_year == "
            "current_session (or blank) count."
        )
    if excluded["status_extra"]:
        reasons.append(
            f"{len(excluded['status_extra'])} row(s) are PENDING or is_extra=True and never count."
        )
    if missing:
        reasons.append(
            f"{len(missing)} month(s) of the 12 have NO paid standard row at all: {missing}."
        )
    if not reasons:
        print("     is_fee_cleared is True - no mismatch found.")
    else:
        for i, r in enumerate(reasons, 1):
            print(f"     [{i}] {r}")
    print(RULE)


def list_students():
    print(f"{'student_id':<12} {'name':<25} {'class':<15} "
          f"{'session':<10} {'paid':>4}/12  is_fee_cleared")
    print("-" * 80)
    for s in Student.objects.select_related("school_class").all():
        print(f"{s.student_id:<12} {s.name[:24]:<25} {str(s.school_class)[:14]:<15} "
              f"{s.current_session:<10} {s.paid_months_count:>4}/12  {s.is_fee_cleared}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "--list":
        list_students()
    else:
        sid = args[0].strip()
        student = Student.objects.filter(student_id__iexact=sid).first()
        if student is None:
            print(f"ERROR: no Student with student_id='{sid}'. Run with --list to see valid IDs.")
            sys.exit(1)
        dump_student(student)

