from django.urls import path
from . import views

app_name = "auth_core"

urlpatterns = [
    path("", views.RootRedirectView.as_view(), name="root"),
    path("auth/login/", views.CustomLoginView.as_view(), name="login"),
    path("auth/logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
