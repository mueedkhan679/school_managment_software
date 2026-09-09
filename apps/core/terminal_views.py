import json
import csv
import io
import zipfile
from datetime import datetime, timedelta
import re
from decimal import Decimal

from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum

from apps.accounts.decorators import admin_required
from apps.classrooms.models import SchoolClass
from apps.students.models import Student, StudentAcademicHistory
from apps.fees.models import StudentFee, FeeStatus
from apps.attendance.models import Attendance
from apps.teachers.models import TeacherSalary, TeacherAttendance

@admin_required
@require_POST
def terminal_command(request):
    try:
        data = json.loads(request.body)
        command = data.get("command", "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON format."})

    if not command:
        return JsonResponse({"status": "error", "message": "Empty command."})

    # Convert command to lower case for parsing where appropriate
    lower_cmd = command.lower()

    # Help command
    if lower_cmd == "help":
        help_html = """
        <div style="margin-left: 10px;">
            <strong>Available Commands:</strong><br>
            <span style="color:#58a6ff;">open class &lt;class_name&gt;</span> - Manage students in a class<br>
            <span style="color:#58a6ff;">show my statement</span> - Generate a financial overview<br>
            <span style="color:#58a6ff;">download all data from &lt;year&gt; to &lt;year&gt;</span> - Export full system data<br>
            <span style="color:#58a6ff;">clear</span> - Clear terminal output<br>
        </div>
        """
        return JsonResponse({"status": "success", "html": help_html})

    # Command A: open class <class_name>
    if lower_cmd.startswith("open class "):
        class_name = command[11:].strip()
        return execute_open_class(class_name)

    # Command A: execute_hard_delete <student_id> (Internal)
    if lower_cmd.startswith("execute_hard_delete "):
        parts = command.split(" ", 1)
        if len(parts) > 1:
            return execute_hard_delete(parts[1].strip())
            
    # Command A: execute_hard_delete_all <class_id> (Internal)
    if lower_cmd.startswith("execute_hard_delete_all "):
        parts = command.split(" ", 1)
        if len(parts) > 1 and parts[1].strip().isdigit():
            return execute_hard_delete_all(int(parts[1].strip()))

    # Command B: show my statement
    if lower_cmd == "show my statement":
        # Prompt for date range
        prompt_html = """
        <div>Please specify a date range by clicking one of the options below:</div>
        <div style="margin-top: 8px; display: flex; gap: 8px;">
            <button onclick="processCommand('execute_statement today')">Today</button>
            <button onclick="processCommand('execute_statement last_7_days')">Last 7 Days</button>
            <button onclick="processCommand('execute_statement this_month')">This Month</button>
            <button onclick="processCommand('execute_statement this_year')">This Year</button>
        </div>
        """
        return JsonResponse({"status": "success", "html": prompt_html})

    # Command B: execute_statement <range> (Internal)
    if lower_cmd.startswith("execute_statement "):
        range_val = command[18:].strip()
        return execute_statement(range_val)

    # Command C: download all data from <start> to <end>
    match = re.match(r"^download all data from (\d{4}) to (\d{4})$", lower_cmd)
    if match:
        start_year = int(match.group(1))
        end_year = int(match.group(2))
        return execute_data_export(start_year, end_year)

    return JsonResponse({
        "status": "error",
        "message": f"Command not found: '{command}'. Type 'help' for available commands."
    })


def execute_open_class(class_name):
    # Case-insensitive search for class
    school_class = SchoolClass.objects.filter(name__iexact=class_name).first()
    if not school_class:
        return JsonResponse({"status": "error", "message": f"Class '{class_name}' not found."})

    students = Student.objects.filter(school_class=school_class).order_by("student_id")
    
    if not students.exists():
        return JsonResponse({
            "status": "success",
            "html": f"<div>Class <strong>{school_class.name}</strong> has no enrolled students.</div>"
        })

    html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span><strong>Class {school_class.name}</strong> - {students.count()} Enrolled</span>
        <button class="danger" onclick="terminalHardDeleteAllStudents({school_class.id})">Delete All Students</button>
    </div>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Status</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
    """
    for student in students:
        status_color = "#27c93f" if student.is_active else "#ffbd2e"
        status_text = "Active" if student.is_active else "Inactive"
        html += f"""
            <tr>
                <td>{student.student_id}</td>
                <td>{student.name}</td>
                <td style="color: {status_color};">{status_text}</td>
                <td><button class="danger" onclick="terminalHardDeleteStudent('{student.student_id}')">Hard Delete</button></td>
            </tr>
        """
    html += "</tbody></table>"

    return JsonResponse({"status": "success", "html": html})


@transaction.atomic
def execute_hard_delete(student_identifier):
    # Can be PK or student_id
    if str(student_identifier).isdigit():
        student = Student.objects.filter(id=int(student_identifier)).first()
    else:
        student = Student.objects.filter(student_id=student_identifier).first()
        
    if not student:
        return JsonResponse({"status": "error", "message": f"Student '{student_identifier}' not found."})

    name = student.name
    stu_id = student.student_id

    # Manually delete related records with PROTECT constraints
    StudentFee.objects.filter(student=student).delete()
    Attendance.objects.filter(student=student).delete()
    StudentAcademicHistory.objects.filter(student=student).delete()
    # If there are other models pointing to Student, delete them here.
    
    student.delete()
    return JsonResponse({
        "status": "success",
        "html": f"<span style='color:#27c93f;'>Successfully hard-deleted {name} ({stu_id}) and all associated records.</span>"
    })


@transaction.atomic
def execute_hard_delete_all(class_id):
    school_class = SchoolClass.objects.filter(id=class_id).first()
    if not school_class:
        return JsonResponse({"status": "error", "message": "Class not found."})
        
    students = Student.objects.filter(school_class=school_class)
    count = students.count()
    
    # Batch delete dependencies for all these students
    student_ids = list(students.values_list('id', flat=True))
    
    StudentFee.objects.filter(student_id__in=student_ids).delete()
    Attendance.objects.filter(student_id__in=student_ids).delete()
    StudentAcademicHistory.objects.filter(student_id__in=student_ids).delete()
    
    # Now delete all students
    students.delete()
    
    return JsonResponse({
        "status": "success",
        "html": f"<span style='color:#27c93f;'>Successfully hard-deleted {count} students from {school_class.name} and all their associated records.</span>"
    })


def execute_statement(range_val):
    now = timezone.now()
    if range_val == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59)
        label = "Today"
    elif range_val == "last_7_days":
        start_date = now - timedelta(days=7)
        end_date = now
        label = "Last 7 Days"
    elif range_val == "this_month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0)
        end_date = now
        label = "This Month"
    elif range_val == "this_year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0)
        end_date = now
        label = "This Year"
    else:
        return JsonResponse({"status": "error", "message": "Invalid date range."})

    # Income from StudentFees
    fees = StudentFee.objects.filter(
        status=FeeStatus.PAID,
        payment_date__gte=start_date.date(),
        payment_date__lte=end_date.date()
    )
    total_income = fees.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Expenses from TeacherSalary
    salaries = TeacherSalary.objects.filter(
        status="PAID",
        payment_date__gte=start_date.date(),
        payment_date__lte=end_date.date()
    )
    total_expenses = salaries.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    net_balance = total_income - total_expenses

    html = f"""
    <div style="margin-top: 8px;">
        <strong>Financial Statement: {label}</strong><br>
        <span style="color:#888;">{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</span>
    </div>
    <table>
        <tr><td>Total Income (Fees)</td><td style="color:#27c93f;">Rs {total_income}</td></tr>
        <tr><td>Total Expenses (Salaries)</td><td style="color:#ff5f56;">Rs {total_expenses}</td></tr>
        <tr><td><strong>Net Balance</strong></td><td><strong>Rs {net_balance}</strong></td></tr>
    </table>
    """
    return JsonResponse({"status": "success", "html": html})


def execute_data_export(start_year, end_year):
    # Determine the session year strings covered by the range
    # e.g., if range is 2026 to 2027, cover sessions '2026-2027', '2027-2028'
    sessions = [f"{year}-{year+1}" for year in range(start_year, end_year + 1)]
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Students Export
        student_csv = io.StringIO()
        writer = csv.writer(student_csv)
        writer.writerow(["ID", "Name", "Father Name", "Class", "Phone", "Status", "Joined"])
        for s in Student.objects.all():
            writer.writerow([
                s.student_id, 
                s.name, 
                s.father_name, 
                s.school_class.name if s.school_class else "-", 
                s.phone, 
                "Active" if s.is_active else "Inactive",
                s.created_at.strftime('%Y-%m-%d')
            ])
        zip_file.writestr("students.csv", student_csv.getvalue())
        
        # 2. Fees Export (Filtered by session years)
        fee_csv = io.StringIO()
        writer = csv.writer(fee_csv)
        writer.writerow(["Student ID", "Student Name", "Class", "Session", "Month", "Amount", "Status", "Payment Date", "Reference"])
        # Handle cases where session might be blank but dates fall in range
        fees = StudentFee.objects.filter(session_year__in=sessions)
        for f in fees:
            writer.writerow([
                f.student.student_id,
                f.student.name,
                f.school_class.name if f.school_class else "-",
                f.session_year,
                f.get_fee_month_display(),
                f.amount,
                f.status,
                f.payment_date.strftime('%Y-%m-%d') if f.payment_date else "-",
                f.reference
            ])
        zip_file.writestr("fees.csv", fee_csv.getvalue())
        
        # 3. Attendance Export (Filtered roughly by dates)
        attendance_csv = io.StringIO()
        writer = csv.writer(attendance_csv)
        writer.writerow(["Date", "Student ID", "Name", "Status", "Marked By"])
        
        # Assuming academic year roughly aligns with start_year to end_year+1
        att_start = datetime(start_year, 1, 1).date()
        att_end = datetime(end_year + 1, 12, 31).date()
        
        attendances = Attendance.objects.filter(date__gte=att_start, date__lte=att_end)
        for a in attendances:
            writer.writerow([
                a.date.strftime('%Y-%m-%d'),
                a.student.student_id,
                a.student.name,
                a.status,
                a.marked_by.username if a.marked_by else "-"
            ])
        zip_file.writestr("attendance.csv", attendance_csv.getvalue())

    zip_buffer.seek(0)
    
    response = HttpResponse(zip_buffer.read(), content_type="application/zip")
    response["Content-Disposition"] = f"attachment; filename=school_data_{start_year}_{end_year}.zip"
    return response
