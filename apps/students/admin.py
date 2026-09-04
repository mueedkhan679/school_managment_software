from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render
from django.http import HttpResponseRedirect
from apps.classrooms.models import SchoolClass
from .models import Student, StudentStatus

@admin.register(Student)

class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'school_class', 'status', 'is_active')
    list_filter = ('school_class', 'status', 'is_active')
    search_fields = ('name', 'student_id', 'roll_number')
    actions = ['promote_students']

    @admin.action(description='Promote selected students to a new class')
    def promote_students(self, request, queryset):
        from apps.fees.models import FeeStatus
        from .models import StudentAcademicHistory
        
        student_info_list = []
        has_incomplete_fees = False

        for student in queryset:
            # Count distinct paid months for the student's CURRENT class
            paid_count = student.fees.filter(
                school_class=student.school_class,
                status=FeeStatus.PAID
            ).values('fee_month').distinct().count()
            
            is_cleared = (paid_count >= 12)
            if not is_cleared:
                has_incomplete_fees = True
                
            latest_fee = student.fees.filter(school_class=student.school_class).order_by('-payment_date').first()
            session_year = latest_fee.session_year if latest_fee else "N/A"
            
            student_info_list.append({
                'student': student,
                'paid_count': paid_count,
                'is_cleared': is_cleared,
                'session_year': session_year
            })

        if 'apply' in request.POST:
            new_class_id = request.POST.get('new_class')
            allow_incomplete = request.POST.get('allow_incomplete_fees') == 'on'
            
            if not new_class_id:
                self.message_user(request, "No class selected.", level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())
                
            if has_incomplete_fees and not allow_incomplete:
                self.message_user(request, "Cannot promote students with incomplete fees unless override is checked.", level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())
                
            new_class = SchoolClass.objects.get(pk=new_class_id)
            updated_count = 0
            
            for info in student_info_list:
                student = info['student']
                
                # 1. Archive the current academic session
                StudentAcademicHistory.objects.create(
                    student=student,
                    school_class=student.school_class,
                    session_year=info['session_year'],
                    fee_clearance_status=f"{info['paid_count']}/12 Paid",
                    status_tag=StudentStatus.PROMOTED
                )
                
                # 2. Advance the student to the new class and reset their status to PROMOTED
                # Because fees are tied to school_class, they will naturally start at 0/12 
                # paid for this new class in the system.
                student.school_class = new_class
                student.status = StudentStatus.PROMOTED
                student.save(update_fields=['school_class', 'status'])
                updated_count += 1

            self.message_user(request, f"Successfully promoted {updated_count} students to {new_class.name}.")
            return HttpResponseRedirect(request.get_full_path())

        classes = SchoolClass.objects.all().order_by('order', 'id')
        return render(
            request,
            'admin/students/promote_students.html',
            context={
                'student_infos': student_info_list,
                'has_incomplete_fees': has_incomplete_fees,
                'classes': classes,
                'action': 'promote_students'
            }
        )
