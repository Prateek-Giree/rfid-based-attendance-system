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
        return context
