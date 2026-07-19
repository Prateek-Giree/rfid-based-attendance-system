from django.urls import path
from . import views
from . import teacher_views

app_name = "auth_core"

urlpatterns = [
    path("", views.RootRedirectView.as_view(), name="root"),
    path("auth/login/", views.CustomLoginView.as_view(), name="login"),
    path("auth/logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),

    # Teachers
    path("teachers/", teacher_views.TeacherListView.as_view(), name="teacher_list"),
    path("teachers/create/", teacher_views.TeacherCreateView.as_view(), name="teacher_create"),
    path("teachers/<int:pk>/", teacher_views.TeacherDetailView.as_view(), name="teacher_detail"),
    path("teachers/<int:pk>/edit/", teacher_views.TeacherUpdateView.as_view(), name="teacher_update"),
    path("teachers/<int:pk>/deactivate/", teacher_views.TeacherDeactivateView.as_view(), name="teacher_deactivate"),
]
