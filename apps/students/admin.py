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
        if 'apply' in request.POST:
            new_class_id = request.POST.get('new_class')
            if not new_class_id:
                self.message_user(request, "No class selected.", level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())
                
            new_class = SchoolClass.objects.get(pk=new_class_id)
            updated = queryset.update(school_class=new_class, status=StudentStatus.PROMOTED)
            self.message_user(request, f"Successfully promoted {updated} students to {new_class.name}.")
            return HttpResponseRedirect(request.get_full_path())

        classes = SchoolClass.objects.all().order_by('order', 'id')
        return render(
            request,
            'admin/students/promote_students.html',
            context={'students': queryset, 'classes': classes, 'action': 'promote_students'}
        )
