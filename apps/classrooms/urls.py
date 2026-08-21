from django.urls import path
from . import views

app_name = "classrooms"

urlpatterns = [
    path("", views.class_list, name="list"),
    path("create/", views.class_create, name="create"),
    path("<int:pk>/", views.class_detail, name="detail"),
    path("<int:pk>/edit/", views.class_update, name="update"),
    path("<int:pk>/delete/", views.class_delete, name="delete"),
]
