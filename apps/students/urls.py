from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("", views.student_list, name="list"),
    path("create/", views.student_create, name="create"),
    path("<str:student_id>/", views.student_detail, name="detail"),
    path("<str:student_id>/edit/", views.student_update, name="update"),
    path("<str:student_id>/delete/", views.student_delete, name="delete"),
    path("<str:student_id>/restore/", views.student_restore, name="restore"),
]
