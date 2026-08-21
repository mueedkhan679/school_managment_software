from django.urls import path
from . import views
from . import id_management_views as id_views

app_name = "accounts"

urlpatterns = [
    path("login/", views.admin_login, name="login"),
    path("logout/", views.admin_logout, name="logout"),
    path("change-credentials/", views.change_credentials, name="change_credentials"),
    # Phase 10 – User Account Management
    path("manage/", id_views.account_list, name="account_list"),
    path("manage/create/", id_views.account_create, name="account_create"),
    path("manage/<int:user_id>/toggle-status/", id_views.account_toggle_status, name="account_toggle_status"),
    path("manage/<int:user_id>/reset-password/", id_views.account_reset_password, name="account_reset_password"),
    path("manage/<int:user_id>/delete/", id_views.account_delete, name="account_delete"),
    # Phase 10 – Printable ID Cards
    path("id-cards/students/", id_views.id_card_batch_students, name="id_card_batch_students"),
    path("id-cards/teachers/", id_views.id_card_batch_teachers, name="id_card_batch_teachers"),
    path("id-cards/student/<str:student_id>/", id_views.id_card_student, name="id_card_student"),
    path("id-cards/teacher/<str:teacher_id>/", id_views.id_card_teacher, name="id_card_teacher"),
]
