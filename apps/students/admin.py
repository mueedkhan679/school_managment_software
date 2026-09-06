from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html

from apps.classrooms.models import SchoolClass
from .models import (
    MONTHS_PER_SESSION,
    Student,
    StudentAcademicHistory,
)


class StudentAcademicHistoryInline(admin.TabularInline):
    """Read-only inline showing archived academic sessions on the student page."""

    model = StudentAcademicHistory
    extra = 0
    can_delete = False
    max_num = 0
    readonly_fields = (
        "school_class",
        "session_year",
        "fee_clearance_status",
        "status_tag",
        "promoted_date",
    )
    verbose_name = "Archived Academic Session"
    verbose_name_plural = "Archived Academic Sessions (permanent record)"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_id",
        "name",
        "school_class",
        "fee_progress",
        "status",
        "is_active",
    )
    list_filter = ("school_class", "status", "is_active")
    search_fields = ("name", "student_id", "roll_number")
    actions = ["promote_students"]
    inlines = [StudentAcademicHistoryInline]

    @admin.display(description="Fee Clearance", ordering="school_class")
    def fee_progress(self, obj):
        """Changelist column showing the live 12-month fee tracker."""
        color = "#1e7e34" if obj.is_fee_cleared else "#b3541e"
        if obj.is_fee_cleared:
            label = f"{MONTHS_PER_SESSION}/{MONTHS_PER_SESSION} Cleared"
        else:
            label = f"{obj.paid_months_count}/{MONTHS_PER_SESSION} Paid"
        return format_html(
            '<span style="color:{}; font-weight:700;">{}</span>'
            '<br><small style="color:#666;">Session {}</small>',
            color,
            label,
            obj.current_session,
        )

    @admin.action(description="Promote selected students to a new class")
    def promote_students(self, request, queryset):
        """Bulk promotion with an intermediate Target-Class confirmation step."""
        student_info_list = []
        has_incomplete_fees = False

        for student in queryset.select_related("school_class").order_by("student_id"):
            is_cleared = student.is_fee_cleared
            if not is_cleared:
                has_incomplete_fees = True
            student_info_list.append(
                {
                    "student": student,
                    "paid_count": student.paid_months_count,
                    "is_cleared": is_cleared,
                    "session_year": student.current_session,
                }
            )

        if "apply" in request.POST:
            new_class_id = request.POST.get("new_class")
            allow_incomplete = request.POST.get("allow_incomplete_fees") == "on"

            if not new_class_id:
                self.message_user(
                    request, "No target class selected.", level=messages.ERROR
                )
                return HttpResponseRedirect(request.get_full_path())

            if has_incomplete_fees and not allow_incomplete:
                self.message_user(
                    request,
                    "Cannot promote students with incomplete fees unless the "
                    "override is checked.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(request.get_full_path())

            try:
                new_class = SchoolClass.objects.get(pk=int(new_class_id))
            except (TypeError, ValueError, SchoolClass.DoesNotExist):
                self.message_user(
                    request, "Selected target class does not exist.", level=messages.ERROR
                )
                return HttpResponseRedirect(request.get_full_path())

            updated_count = 0
            skipped_count = 0
            for info in student_info_list:
                student = info["student"]
                if student.school_class_id == new_class.pk:
                    skipped_count += 1
                    continue
                # Archives the finished class/session and resets the tracker.
                student.promote_to(new_class, force=allow_incomplete)
                updated_count += 1

            message = (
                f"Successfully promoted {updated_count} students to {new_class.name}."
            )
            if skipped_count:
                message += (
                    f" {skipped_count} student(s) already in {new_class.name} "
                    "were skipped."
                )
            self.message_user(request, message)
            return HttpResponseRedirect(request.get_full_path())

        classes = SchoolClass.objects.order_by("order", "id")
        return render(
            request,
            "admin/students/promote_students.html",
            context={
                "student_infos": student_info_list,
                "has_incomplete_fees": has_incomplete_fees,
                "classes": classes,
                "action": "promote_students",
                "opts": self.model._meta,
            },
        )
# ------------------------------------------------------------------
    # Per-student promotion workflow (Target Class dropdown)
    # ------------------------------------------------------------------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/promote/",
                self.admin_site.admin_view(self.promote_student_view),
                name="students_student_promote",
            ),
        ]
        return custom_urls + urls

    def promote_student_view(self, request, object_id):
        """Intermediate page to choose the Target Class, then archive the
        current academic session and move the student."""
        student = get_object_or_404(Student, pk=object_id)

        if request.method == "POST" and request.POST.get("apply"):
            new_class_id = request.POST.get("new_class", "").strip()
            allow_incomplete = request.POST.get("allow_incomplete_fees") == "on"

            if not new_class_id:
                self.message_user(
                    request, "Please select a target class.", level=messages.ERROR
                )
                return HttpResponseRedirect(request.get_full_path())

            try:
                new_class = SchoolClass.objects.get(pk=int(new_class_id))
            except (TypeError, ValueError, SchoolClass.DoesNotExist):
                self.message_user(
                    request, "Selected target class does not exist.", level=messages.ERROR
                )
                return HttpResponseRedirect(request.get_full_path())

            if new_class.pk == student.school_class_id:
                self.message_user(
                    request,
                    f"{student.name} is already enrolled in {new_class.name}.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(request.get_full_path())

            if not student.is_fee_cleared and not allow_incomplete:
                self.message_user(
                    request,
                    f"{student.name} has not completed all {MONTHS_PER_SESSION} "
                    f"months of fees for {student.school_class.name} (Session "
                    f"{student.current_session}). Check the override below to "
                    "promote anyway.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(request.get_full_path())

            archived = student.promote_to(new_class, force=allow_incomplete)
            self.message_user(
                request,
                f"{student.name} ({student.student_id}) promoted from "
                f"{archived.school_class} (Session {archived.session_year} · "
                f"'{archived.fee_clearance_status}') to {new_class.name}. Status "
                "set to PROMOTED and the fee tracker reset to 0/12 for the new "
                "session.",
            )
            return HttpResponseRedirect(
                reverse("admin:students_student_change", args=[student.pk])
            )

        classes = SchoolClass.objects.exclude(pk=student.school_class_id).order_by(
            "order", "id"
        )
        context = {
            **self.admin_site.each_context(request),
            "student": student,
            "classes": classes,
            "has_promotable_classes": classes.exists(),
            "fee_clearance": {
                "paid_count": student.paid_months_count,
                "total_months": MONTHS_PER_SESSION,
                "is_cleared": student.is_fee_cleared,
                "session_year": student.current_session,
                "status_label": student.fee_clearance_status,
            },
            "opts": self.model._meta,
            "has_change_permission": self.has_change_permission(request, student),
        }
        return render(request, "admin/students/promote_student.html", context)

    # ------------------------------------------------------------------
    # Change page: fee-clearance highlight + active Promote button
    # ------------------------------------------------------------------
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        student = self.get_object(request, object_id)
        if student is not None:
            promotable_classes = SchoolClass.objects.exclude(
                pk=student.school_class_id
            ).count()
            extra_context.update(
                {
                    "fee_clearance": {
                        "paid_count": student.paid_months_count,
                        "total_months": MONTHS_PER_SESSION,
                        "is_cleared": student.is_fee_cleared,
                        "session_year": student.current_session,
                        "status_label": student.fee_clearance_status,
                    },
                    "promote_url": reverse(
                        "admin:students_student_promote", args=[student.pk]
                    ),
                    "has_promotable_classes": promotable_classes > 0,
                }
            )
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )