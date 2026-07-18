from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class AdminRequiredMixin(LoginRequiredMixin):
    """
    Restricts access to staff (Admin) users only.
    Unauthenticated users are redirected to LOGIN_URL.
    Non-staff authenticated users receive a 403.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class TeacherRequiredMixin(LoginRequiredMixin):
    """
    Restricts access to Teachers and Admins.
    - Admins (is_staff=True) always pass.
    - Teachers (has teacher_profile relation) pass.
    - Everyone else receives a 403.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        is_admin = request.user.is_staff
        is_teacher = hasattr(request.user, "teacher_profile")
        if not (is_admin or is_teacher):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
