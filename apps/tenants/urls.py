"""URL routes for the Master Admin portal."""

from django.urls import path
from . import admin_views

app_name = "tenants"

urlpatterns = [
    path("", admin_views.master_dashboard, name="master_dashboard"),
    path("add/", admin_views.school_add, name="school_add"),
    path("<slug:slug>/edit/", admin_views.school_edit, name="school_edit"),
    path("<slug:slug>/toggle/", admin_views.school_toggle, name="school_toggle"),
    path("<slug:slug>/lock/", admin_views.school_lock, name="school_lock"),
    path("<slug:slug>/reset-password/", admin_views.school_reset_password, name="school_reset_password"),
    path("<slug:slug>/delete/", admin_views.school_delete, name="school_delete"),
]
