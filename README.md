# School Management Software

A modern, professional, secure, web-based School Management Software built with **Django 6.1** and **SQLite**.

> Note: this project was set up on a Windows machine where Python is launched via the `py` launcher
> (the bare `python` command is a Microsoft Store stub). Run all commands below with `py`.

## Features (roadmap by phase)

- **Phase 1 — Architecture & Database (COMPLETED):**
  - Modular Django project (`config` + `apps` package) with seven apps:
    `accounts`, `classrooms`, `students`, `teachers`, `fees`, `attendance`, `core`.
  - Relational schema with foreign keys, unique constraints, check constraints and indexes.
  - Automatic, permanent, never-reused IDs: `STU-000001` / `TCH-000001` (atomic `Sequence` counters).
  - Custom `User` model with role-based access (`ADMIN` / `TEACHER` / `STUDENT`); PBKDF2 password hashing.
  - Class catalog seeded via data migration: Playgroup, Nursery, KG, Class 1 ... Class 12.
  - Initial admin seeded via data migration: `admin` / `admin123`.
  - Soft-delete `is_active` flags on Student/Teacher so financial/attendance history is never lost.
  - DB-level duplicate protection: one fee per student+month+year (unless `is_extra`), one attendance per student+date, positive amounts.
- **Phase 2 — Admin Authentication** *(pending)*
- **Phase 3 — Dashboard** *(pending)*
- **Phase 4 — Class Management** *(pending)*
- **Phase 5 — Student Management** *(pending)*
- **Phase 6 — Student Fee Management** *(pending)*
- **Phase 7 — Financial Reports** *(pending)*
- **Phase 8 — Teacher Management** *(pending)*
- **Phase 9 — Teacher Salary Management** *(pending)*
- **Phase 10 — User/ID Management** *(pending)*
- **Phase 11 — Attendance System** *(pending)*
- **Phase 12 — Teacher Attendance App** *(pending)*
- **Phase 13 — Student App** *(pending)*
- **Phase 14 — Security Hardening** *(pending)*
- **Phase 15 — Testing & Bug Fixing** *(pending)*
- **Phase 16 — UI/UX Polishing** *(pending)*

## Getting Started

```bat
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

Open http://127.0.0.1:8000/

**Initial admin credentials:** `admin` / `admin123` (change after first login — planned for Phase 2).

### Offline install bootstrap (if PyPI is slow/unreachable)

The exact wheels used to build this project are cached in `wheels/`
(SHA-256 verified). Install without the network with:

```bat
py -m pip install --no-index --find-links wheels django asgiref sqlparse
```

`download_wheels.py` re-downloads/verifies wheels from a mirror if the cache is ever removed.

## Project Structure

```
school_project/
├── config/          # Django project settings, URLs
├── apps/
│   ├── accounts/    # Custom User model + roles (ADMIN/TEACHER/STUDENT)
│   ├── core/        # Shared helpers (ID Sequence), landing page
│   ├── classrooms/  # SchoolClass catalog + monthly fees
│   ├── students/    # Student records + unique STU-* IDs
│   ├── teachers/    # Teachers + salaries + assigned classes
│   ├── fees/        # Student fee payments (income)
│   └── attendance/  # Attendance records
├── templates/       # Shared templates
├── static/          # CSS/JS/assets
├── media/           # Uploaded images (student/teacher photos, CNIC)
├── wheels/          # Verified offline wheels (bootstrap)
└── db.sqlite3       # SQLite database
```

## Database Schema (Phase 1)

| Table | Purpose |
|---|---|
| `accounts_user` | Users with role (`ADMIN`/`TEACHER`/`STUDENT`), hashed passwords |
| `classrooms_schoolclass` | Classes (Playgroup→Class 12) with monthly fee |
| `students_student` | Students with unique `STU-*` ID, class FK, optional fee override |
| `teachers_teacher` | Teachers with unique `TCH-*` ID, salary, assigned classes |
| `teachers_teachersalary` | Salary payments (expenses), unique per teacher+month+year |
| `fees_studentfee` | Fee payments (income), unique per student+month+year unless `is_extra` |
| `attendance_attendance` | Attendance per student+date (unique), marked-by link |
| `core_sequence` | Atomic counters guaranteeing permanent, non-reused IDs |

Key integrity rules enforced at the database level:
- `unique_student_fee_month` — blocks accidental duplicate fee entries (partial unique index where `is_extra = 0`).
- `unique_student_attendance_date` — one attendance record per student per day.
- `unique_teacher_salary_month` — one salary payment per teacher per month.
- `fee_amount_positive` / `salary_amount_positive` — no zero/negative payments.

