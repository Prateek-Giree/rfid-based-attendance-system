from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login as auth_login
from django.urls import reverse_lazy
from django.views.generic import RedirectView, TemplateView
from django.views.generic.edit import FormView
from django.shortcuts import redirect
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from .forms import LoginForm, ForgotPasswordForm, VerifyOTPForm, ResetPasswordForm
from apps.auth_core.models import User
from .services.otp_service import OTPService


class RootRedirectView(RedirectView):
    """Redirects / to dashboard if authenticated, otherwise to login."""

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return reverse_lazy("auth_core:dashboard")
        return reverse_lazy("auth_core:login")


class CustomLoginView(LoginView):
    """Email-based login. Implements two-step OTP verification."""

    template_name = "auth_core/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("auth_core:dashboard")

    def form_valid(self, form):
        user = form.get_user()
        try:
            otp = OTPService.generate_otp(user, "login", expiry_minutes=5)
            OTPService.send_otp_email(user, "login", otp)
            self.request.session["pre_otp_user_id"] = user.id
            messages.info(self.request, "An OTP has been sent to your email. Please verify.")
            return redirect("auth_core:verify_login_otp")
        except ValidationError as e:
            messages.error(self.request, e.message)
            return super().form_invalid(form)
        except Exception:
            messages.error(self.request, "Failed to send OTP email. Please try again later.")
            return super().form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid email or password. Please try again.")
        return super().form_invalid(form)


@method_decorator(never_cache, name='dispatch')
class VerifyLoginOTPView(FormView):
    template_name = "auth_core/verify_login_otp.html"
    form_class = VerifyOTPForm
    success_url = reverse_lazy("auth_core:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("pre_otp_user_id"):
            messages.error(request, "Session expired. Please log in again.")
            return redirect("auth_core:login")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.session.get("pre_otp_user_id")
        user = User.objects.filter(id=user_id).first()
        if user:
            context["email"] = user.email
        return context

    def form_valid(self, form):
        user_id = self.request.session.get("pre_otp_user_id")
        user = User.objects.filter(id=user_id).first()
        if not user:
            messages.error(self.request, "User not found.")
            return redirect("auth_core:login")
            
        otp_code = form.cleaned_data["otp_code"]
        
        if OTPService.verify_otp(user, "login", otp_code):
            auth_login(self.request, user)
            del self.request.session["pre_otp_user_id"]
            messages.success(self.request, "Welcome back! You are now logged in.")
            return super().form_valid(form)
        else:
            messages.error(self.request, "Invalid or expired OTP.")
            return super().form_invalid(form)


@method_decorator(never_cache, name='dispatch')
class ForgotPasswordView(FormView):
    template_name = "auth_core/forgot_password.html"
    form_class = ForgotPasswordForm
    success_url = reverse_lazy("auth_core:verify_reset_otp")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        user = User.objects.filter(email=email).first()
        
        if user:
            try:
                otp = OTPService.generate_otp(user, "password_reset", expiry_minutes=10)
                OTPService.send_otp_email(user, "password_reset", otp)
                self.request.session["reset_email"] = email
                messages.success(self.request, "A password reset OTP has been sent to your email.")
                return super().form_valid(form)
            except ValidationError as e:
                messages.error(self.request, e.message)
                return super().form_invalid(form)
            except Exception:
                messages.error(self.request, "Failed to send email. Please try again later.")
                return super().form_invalid(form)
        else:
            # Prevent email enumeration: act like it succeeded
            messages.success(self.request, "If the email exists, an OTP has been sent.")
            return super().form_valid(form)


@method_decorator(never_cache, name='dispatch')
class VerifyPasswordOTPView(FormView):
    template_name = "auth_core/verify_reset_otp.html"
    form_class = VerifyOTPForm
    success_url = reverse_lazy("auth_core:reset_password")

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("reset_email"):
            messages.error(request, "Session expired. Please start over.")
            return redirect("auth_core:forgot_password")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email"] = self.request.session.get("reset_email")
        return context

    def form_valid(self, form):
        email = self.request.session.get("reset_email")
        user = User.objects.filter(email=email).first()
        if not user:
            return redirect("auth_core:forgot_password")
            
        otp_code = form.cleaned_data["otp_code"]
        
        if OTPService.verify_otp(user, "password_reset", otp_code):
            # Give permission to reset password
            self.request.session["can_reset_password"] = True
            return super().form_valid(form)
        else:
            messages.error(self.request, "Invalid or expired OTP.")
            return super().form_invalid(form)


@method_decorator(never_cache, name='dispatch')
class ResetPasswordView(FormView):
    template_name = "auth_core/reset_password.html"
    form_class = ResetPasswordForm
    success_url = reverse_lazy("auth_core:login")

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("can_reset_password") or not request.session.get("reset_email"):
            messages.error(request, "Session expired. Please start over.")
            return redirect("auth_core:forgot_password")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = self.request.session.get("reset_email")
        user = User.objects.filter(email=email).first()
        if user:
            new_password = form.cleaned_data["new_password"]
            user.set_password(new_password)
            user.save()
            messages.success(self.request, "Password reset successfully. You can now log in.")
        
        # Clear session vars
        self.request.session.pop("reset_email", None)
        self.request.session.pop("can_reset_password", None)
        
        return super().form_valid(form)


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
