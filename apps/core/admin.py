from django.contrib import admin

from .forms import SchoolSettingsForm  # noqa: F401  (re-exported for admin convenience)
from .models import SchoolSettings


@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    """Admin panel for the singleton school-branding record."""

    list_display = ("school_name", "school_phone", "updated_at")
    fieldsets = (
        ("Branding", {"fields": ("school_name", "school_logo")}),
        ("Contact", {"fields": ("school_phone",)}),
    )

    def has_add_permission(self, request):
        # Singleton: only allow adding when no row exists yet.
        return not SchoolSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

