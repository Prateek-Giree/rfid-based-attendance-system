from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import RedirectView, TemplateView

from .forms import LoginForm


class RootRedirectView(RedirectView):
    """Redirects / to dashboard if authenticated, otherwise to login."""

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return reverse_lazy("auth_core:dashboard")
        return reverse_lazy("auth_core:login")


class CustomLoginView(LoginView):
    """Email-based login. Redirects authenticated users away immediately."""

    template_name = "auth_core/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("auth_core:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Welcome back! You are now logged in.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid email or password. Please try again.")
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """Logs out and adds a success message before redirecting."""

    next_page = reverse_lazy("auth_core:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, "You have been logged out successfully.")
        return super().dispatch(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard. Single URL for both Admin and Teacher roles.
    Template renders role-aware content via is_admin / is_teacher context vars.
    """

    template_name = "auth_core/dashboard.html"
    login_url = reverse_lazy("auth_core:login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Dashboard"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": None},
        ]

        from apps.students.services import StudentService
        from apps.auth_core.services import TeacherService
        from apps.attendance.services.device_service import DeviceService
        from apps.attendance.services.attendance_service import AttendanceService

        student_stats = StudentService.get_student_stats(self.request.user)
        teacher_stats = TeacherService.get_teacher_stats(self.request.user)
        device_stats = DeviceService.get_device_stats(self.request.user)
        attendance_stats = AttendanceService.get_attendance_stats(self.request.user)

        context.update(student_stats)
        context.update(teacher_stats)
        context.update(device_stats)
        context.update(attendance_stats)

        return context


class DashboardChartsView(LoginRequiredMixin, TemplateView):
    """
    Returns HTMX partial for dashboard charts (Chart.js).
    Loads all analytics: trend, distribution, classroom comparison,
    student distribution, device status, and attendance source.
    """

    template_name = "auth_core/partials/dashboard_charts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.attendance.services.analytics_service import AnalyticsService
        import datetime

        days = int(self.request.GET.get("days", 30))
        classroom_id = self.request.GET.get("classroom", "")

        try:
            date_str = self.request.GET.get("date", "")
            date = datetime.date.fromisoformat(date_str) if date_str else None
        except ValueError:
            date = None

        context["trend_data"] = AnalyticsService.get_attendance_trend_data(
            self.request.user, days=days, classroom_id=classroom_id
        )
        context["distribution_data"] = AnalyticsService.get_present_vs_absent_data(
            self.request.user, date=date, classroom_id=classroom_id
        )
        context["comparison_data"] = AnalyticsService.get_classroom_comparison_data(
            self.request.user, date=date
        )
        context["student_distribution_data"] = AnalyticsService.get_student_distribution_data(
            self.request.user
        )
        context["device_status_data"] = AnalyticsService.get_device_status_breakdown(
            self.request.user
        )
        context["source_data"] = AnalyticsService.get_attendance_source_breakdown(
            self.request.user, days=days
        )

        return context
