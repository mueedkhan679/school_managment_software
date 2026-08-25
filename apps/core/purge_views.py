from datetime import datetime
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from apps.accounts.decorators import admin_required

from apps.students.models import Student
from apps.teachers.models import Teacher, TeacherSalary, TeacherAttendance
from apps.classrooms.models import SchoolClass
from apps.attendance.models import Attendance
from apps.fees.models import StudentFee
from apps.core.models import Sequence

@admin_required
@require_POST
def system_reset(request):
    password = request.POST.get('password')
    if not password or not check_password(password, request.user.password):
        messages.error(request, "Incorrect admin password. System reset aborted.")
        return redirect("accounts:change_credentials")

    reset_scope = request.POST.get('reset_scope')

    try:
        with transaction.atomic():
            if reset_scope == 'ALL':
                # Order of deletion is somewhat important if there are foreign keys,
                # though Django handles most cascading deletes if on_delete=CASCADE.
                StudentFee.objects.all().delete()
                TeacherSalary.objects.all().delete()
                Attendance.objects.all().delete()
                TeacherAttendance.objects.all().delete()
                
                Student.objects.all().delete()
                Teacher.objects.all().delete()
                SchoolClass.objects.all().delete()
                
                Sequence.objects.all().delete()
                
                messages.success(request, "Factory Reset complete. All operational data purged.")
                
            elif reset_scope == 'FILTERED':
                module = request.POST.get('module')
                start_date_str = request.POST.get('start_date')
                end_date_str = request.POST.get('end_date')
                
                if not start_date_str or not end_date_str:
                    messages.error(request, "Start and end dates are required for filtered purge.")
                    return redirect("accounts:change_credentials")
                    
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                
                if module == 'STUDENT_ATTENDANCE':
                    deleted, _ = Attendance.objects.filter(date__gte=start_date, date__lte=end_date).delete()
                elif module == 'TEACHER_ATTENDANCE':
                    deleted, _ = TeacherAttendance.objects.filter(date__gte=start_date, date__lte=end_date).delete()
                elif module == 'FEE_TRANSACTIONS':
                    deleted_fees, _ = StudentFee.objects.filter(payment_date__gte=start_date, payment_date__lte=end_date).delete()
                    deleted_salaries, _ = TeacherSalary.objects.filter(payment_date__gte=start_date, payment_date__lte=end_date).delete()
                    deleted = deleted_fees + deleted_salaries
                elif module == 'ALL_LOGS':
                    a, _ = Attendance.objects.filter(date__gte=start_date, date__lte=end_date).delete()
                    b, _ = TeacherAttendance.objects.filter(date__gte=start_date, date__lte=end_date).delete()
                    c, _ = StudentFee.objects.filter(payment_date__gte=start_date, payment_date__lte=end_date).delete()
                    d, _ = TeacherSalary.objects.filter(payment_date__gte=start_date, payment_date__lte=end_date).delete()
                    deleted = a + b + c + d
                else:
                    messages.error(request, "Invalid module selected.")
                    return redirect("accounts:change_credentials")
                    
                messages.success(request, f"Filtered Purge complete. {deleted} records deleted from {start_date} to {end_date}.")
            else:
                messages.error(request, "Invalid reset scope.")
    except Exception as e:
        messages.error(request, f"An error occurred during purge: {e}")
        
    return redirect("accounts:change_credentials")
