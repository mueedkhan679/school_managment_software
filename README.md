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
- **Phase 2 — Admin Authentication (COMPLETED):**
  - Custom secure admin login (`/accounts/login/`) with a modern responsive UI, CSRF protection,
    clear error messages (invalid credentials / disabled account / non-admin role), and `next`-aware
    redirects that block open redirects.
  - Role-based access control decorators (`role_required`, `admin_required`) — anonymous users are
    redirected to login with `?next=...`; non-admins receive 403.
  - Session security: session key rotation on login (anti-fixation), 8h expiry, browser-close expiry,
    `HttpOnly` + `SameSite=Lax` cookies, POST-only logout that flushes the session.
  - Change Credentials page (`/accounts/change-credentials/`): verify current password, change
    username/password, enforce password strength via Django validators, PBKDF2-hash new passwords,
    keep the session valid after the change.
  - Top navigation bar with logged-in user chip and secure logout button.
  - Automated test suite (24 tests) covering login, access control, logout, credential changes,
    CSRF presence, session-key rotation and XSS escaping.
- **Phase 3 — Dashboard (COMPLETED):**
  - Real database-driven dashboard statistics: active students, total classes, active teachers,
    current month and yearly fee income, monthly teacher salary expenses, net balance / income,
    and today's attendance metrics.
  - Interactive clickable stat cards navigating to relevant sections.
  - Class statistics overview with real-time enrolled student count badges and quick student inspector.
  - Recent fee receipts and teacher salary disbursement lists.
- **Phase 4 — Class Management (COMPLETED):**
  - Full CRUD operations for classes at `/classrooms/`.
  - Class listing with active enrolled student counts, assigned teachers, and fee structures.
  - "Add New Class" modal with live validation (unique name, positive fee, order).
  - Class detail view showing fee breakdown, expected monthly/yearly income, assigned faculty, and enrolled student roster.
  - Edit class page with pre-filled forms and error handling.
  - Cascade safety protection preventing deletion of classes that have enrolled students (`models.PROTECT`).
  - Top navigation bar links with active route indicators.
  - Automated test suite (11 dedicated tests) covering RBAC, list, create, detail, edit, and safe deletion.
- **Phase 5 — Student Management (COMPLETED):**
  - Full CRUD operations for students at `/students/`.
  - Atomic, auto-generated, permanent student IDs (`STU-000001`, `STU-000002`) using database `Sequence` counters (never reuses IDs).
  - Search & filter capabilities: query by Student ID, Name, Father Name, Form-B, Phone; filter by Class & Active/Inactive status.
  - Multi-part student registration & profile edit forms with image upload validation (JPG/PNG/WEBP, 5MB limit).
  - Comprehensive Student Profile view (`/students/<student_id>/`) featuring personal bio-data, B-Form info, real-time fee payment status & history, attendance rate & logs, and print layout (`window.print()`).
  - Soft-delete mechanism (`is_active=False`) preserving historical fee vouchers and attendance records, with one-click restore.
  - Automated test suite (12 dedicated tests) covering RBAC, auto-ID generation, search/filter, image validation, updates, and soft-delete/restore.
- **Phase 6 — Student Fee Management (COMPLETED):**
  - Fee collection and transaction recording at `/fees/create/` with dynamic student selection and rate lookup.
  - Transaction ledger at `/fees/` with filtering by Month, Year, Class, Payment Status, and text search (Student ID, Name, Receipt #).
  - Strict duplicate payment and overpayment protection at both form and database constraint levels (duplicate month/year blocked unless explicitly marked as `is_extra=True`).
  - Automatic sequential receipt voucher number generation (`REC-YYYYMM-XXXX`).
  - Official printable Fee Receipt Voucher view (`/fees/<id>/`) with student bio, breakdown, annual dues standing, cashier/principal signature blocks, and clean `@media print` styling.
  - Student Profile integration: interactive 12-month calendar matrix (Jan-Dec) on `/students/<id>/` displaying real-time paid vs. unpaid statuses with direct one-click fee collection links.
  - Automated test suite (12 dedicated tests) covering RBAC, search/filter, duplicate blocking, `is_extra` handling, voucher rendering, updates, and student fee info API.
- **Phase 7 — Financial Reports & Analytics (COMPLETED):**
  - Comprehensive financial reporting dashboard at `/reports/`.
  - Core financial KPIs: Today's Fee Collections, Monthly Collections, Annual Collections, Total Pending Annual Student Dues, Total Teacher Salary Expenditures, and Net Balance / Profit & Loss.
  - Month-by-month annual audit statement (Jan to Dec breakdown) tracking monthly revenue vs salary expense and net surplus/deficit indicators.
  - Class-wise revenue analysis table calculating active student enrollment, monthly/annual expected tuition, actual collections, outstanding dues, and recovery rates (%).
  - Multi-parameter filtering by Month, Year, and Class.
  - Print-ready financial audit layout with `@media print` styling.
  - Automated test suite covering RBAC, KPI metrics, profit/loss calculations, and class-level filters.
- **Phase 8 — Teacher Management (COMPLETED):**
  - Full CRUD operations for teaching faculty at `/teachers/`.
  - Atomic, auto-generated, sequential teacher IDs (`TCH-000001`, `TCH-000002`) via database `Sequence` counters (never reuses IDs).
  - Teacher directory with search by ID, Name, CNIC, Phone, and filters for Class and Status.
  - Multi-part registration and edit form with multiple class assignments, salary settings, and document/photo uploads with file format/size validation (JPG/PNG/WEBP, 5MB).
  - Comprehensive Teacher Profile view (`/teachers/<id>/`) with bio-data, assigned class badges, CNIC document previews, and annual salary ledger.
  - Soft-delete (`is_active=False`) and restoration preserving all historical payroll and attendance logs.
- **Phase 9 — Teacher Salary Management (COMPLETED):**
  - Teacher salary disbursement system at `/teachers/salaries/create/` with dynamic rate pre-filling.
  - Duplicate salary protection preventing multiple salary payments for the same teacher + month + year.
  - Salary ledger at `/teachers/salaries/` with search and filters by Month, Year, and Payment Status.
  - Automated expense deduction logic: teacher salary payments automatically feed into financial reports, dashboard expenses, and net balance.
  - Official printable Salary Payslip Voucher (`/teachers/salaries/<id>/`) with faculty details, disbursement particulars, annual dues standing, signature blocks, and `@media print` styling.
  - Automated test suite (14 dedicated tests) covering RBAC, auto-ID generation, search/filter, duplicate blocking, voucher rendering, and API.
- **Phase 10 — User / ID Management (COMPLETED):**
  - Central user account management interface at `/accounts/manage/` — listing all Student/Teacher system accounts with search, role filter, and status filter.
  - Create & Link Account modal: links active Students or Teachers to a unique system login account with unique username enforcement, PBKDF2 password hashing, and role assignment (`STUDENT` or `TEACHER`).
  - Account status toggle (`Active` / `Disabled`) with immediate effect.
  - Admin quick password reset view (`/accounts/manage/<id>/reset-password/`) — sets new PBKDF2-hashed password for any Student/Teacher account.
  - Account deletion (permanently removes user record; linked student/teacher profile preserved).
  - Printable Individual Student ID Card (`/accounts/id-cards/student/<STU-ID>/`) and Teacher ID Card (`/accounts/id-cards/teacher/<TCH-ID>/`) with photo, bio-data, and school branding.
  - Batch/Class-wise Student ID Card print view (`/accounts/id-cards/students/?class_id=X`) — renders up to 10 wallet-sized ID cards per A4 page with clean `@media print` layout.
  - Batch Teacher ID Card print view (`/accounts/id-cards/teachers/`) for entire active faculty roster.
  - "ID Mgmt" navigation link added to top navbar.
  - Automated test suite (16 dedicated tests) covering RBAC, account creation, duplicate username blocking, status toggle, password reset, account deletion, admin protection, and all ID card views.
- **Phase 11 — Attendance System (COMPLETED):**
  - Centralized admin attendance records management at `/attendance/` and daily class roster marking interface at `/attendance/mark/`.
  - Multi-parameter filtering by Date, Month, Year, Class, Student (`STU-XXXXXX` ID / Name), and Teacher who marked attendance.
  - Database constraint enforcement (`unique_student_attendance_date`) prevents duplicate daily attendance entries via `update_or_create` upsert logic.
  - Automatic student attendance statistics calculation: Total Days, Present Count, Absent Count, Attendance Percentage (%).
  - Live attendance metrics integrated directly into the Student Profile view (`/students/<id>/`).
- **Phase 12 — Teacher Portal App (COMPLETED):**
  - Dedicated mobile-friendly web app interface at `/teacher-portal/` for logged-in Teachers (`TEACHER` role).
  - Strict Access Control: Teachers ONLY see their assigned classes and students in those classes; access to financials, admin settings, or non-assigned classes is blocked (`403 Forbidden`).
  - Teacher dashboard with assigned class cards, quick attendance marking with touch-friendly Present/Absent toggles (`marked_by=request.user`), and historical attendance log viewer.
- **Phase 13 — Student Portal App (COMPLETED):**
  - Dedicated mobile-friendly web app interface at `/student-portal/` for logged-in Students (`STUDENT` role).
  - Strict Access Control: Students strictly see ONLY their own personal profile and records; other students' data and admin endpoints return `403 Forbidden`.
  - Personal dashboard displaying photo, bio-data, Class, and Student ID (`STU-XXXXXX`).
  - Fee Summary: Fee status, 12-month calendar schedule matrix for the current year, payment history ledger, and pending annual balance.
  - Attendance Summary: Total attendance days, Present/Absent counts, attendance rate (%), and monthly breakdown log.
- **Phase 14 — Security Hardening (COMPLETED):**
  - Brute-force & Rate-Limiting protection on `/accounts/login/`: Locks out authentication after 5 consecutive failed attempts for 5 minutes via Django cache.
  - CSRF protection enforced on all form submissions and POST requests; auto-escaping enabled with `escapejs` on inline JavaScript strings.
  - Server-side file upload security: Validates image extensions (JPG, PNG, WEBP) and enforces a 5MB maximum file size limit on student/teacher photos and CNIC uploads.
  - Session Security: `HttpOnly` cookies, `SameSite=Lax`, session key rotation on login (anti-fixation), 8h expiry, browser-close expiry, and POST-only logout session flushing.
- **Phase 15 — Automated Testing & Edge-Case Bug Fixing (COMPLETED):**
  - Comprehensive automated test suite (117 tests) covering all 16 phases.
  - Edge-case verification: Zero/negative amount input validation, duplicate protection under DB unique constraints, soft-deleted student/teacher historical record retention, and full RBAC matrix access checks.
  - 100% test pass rate achieved across the entire test suite.
- **Phase 16 — Final UI/UX Polishing (COMPLETED):**
  - Clean, modern, responsive school design system across Desktop, Tablet, and Mobile devices.
  - Smooth CSS animations, touch-friendly UI toggles, loading indicators, empty states, and toast notifications.
  - Audited `@media print` layout overrides for Fee Receipts, Salary Payslips, Financial Audit Reports, and Student/Teacher ID Cards.

## Getting Started

```bat
py -m pip install -r requirements.txt
py manage.py migrate
py manage.py runserver
```

Open http://127.0.0.1:8000/

**Initial admin credentials:** `admin` / `admin123` (change after first login from the Change
Credentials page).

### Running the automated tests

The test suite uses a fast MD5 hasher so it runs quickly (production keeps PBKDF2):

```bat
py manage.py test --settings=config.settings_test
```

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

