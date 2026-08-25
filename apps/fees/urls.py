from django.urls import path
from . import views

app_name = "fees"

urlpatterns = [
    path("", views.fee_list, name="list"),
    path("create/", views.fee_create, name="create"),
    path("defaulter-list/", views.defaulter_list, name="defaulter_list"),
    path("defaulter-list/print/", views.defaulter_list_print, name="defaulter_list_print"),
    path("<int:pk>/", views.fee_voucher, name="voucher"),
    path("<int:pk>/edit/", views.fee_update, name="update"),
    path("<int:pk>/delete/", views.fee_delete, name="delete"),
    path("api/student-info/<int:student_id>/", views.api_student_fee_info, name="api_student_fee_info"),
]
