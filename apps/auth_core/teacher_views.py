from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView, View

from apps.core.mixins import AdminRequiredMixin
from .models import Teacher
from .services import TeacherService
from .teacher_forms import TeacherForm


# ── TEACHER VIEWS ─────────────────────────────────────────────────────────────

class TeacherListView(AdminRequiredMixin, ListView):
    """
    Renders paginated list of all teachers.
    - Admin only.
    - Supports live searching via HTMX partial updates.
    """

    model = Teacher
    paginate_by = 10
    context_object_name = "teachers"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["auth_core/teachers/partials/teacher_table.html"]
        return ["auth_core/teachers/teacher_list.html"]

    def get_queryset(self):
        queryset = Teacher.objects.select_related("user").prefetch_related(
            "classrooms"
        )
        q = self.request.GET.get("q", "").strip()
        queryset = TeacherService.search_teachers(queryset, q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Teachers"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Teachers", "url": None},
        ]
        context["q"] = self.request.GET.get("q", "").strip()
        return context


class TeacherDetailView(LoginRequiredMixin, DetailView):
    """
    Renders detailed profile of a teacher.
    - Admins can view any teacher profile.
    - Teachers can only view their own profile.
    """

    model = Teacher
    context_object_name = "teacher"
    template_name = "auth_core/teachers/teacher_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.is_staff:
            return obj
        if hasattr(user, "teacher_profile") and obj.pk == user.teacher_profile.pk:
            return obj
        raise PermissionDenied("You do not have permission to view this profile.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.object
        classrooms = teacher.classrooms.all()
        from apps.students.models import Student
        student_count = Student.objects.filter(
            classroom__class_teacher=teacher
        ).count()
        context["classrooms"] = classrooms
        context["student_count"] = student_count
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Teachers", "url": reverse_lazy("auth_core:teacher_list")},
            {"label": str(teacher), "url": None},
        ]
        return context


class TeacherCreateView(AdminRequiredMixin, TemplateView):
    """
    Renders creation form and handles teacher + user account creation.
    - Admin only.
    """

    template_name = "auth_core/teachers/teacher_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form", TeacherForm())
        context["page_title"] = "Add Teacher"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Teachers", "url": reverse_lazy("auth_core:teacher_list")},
            {"label": "Add", "url": None},
        ]
        return context

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        form = TeacherForm(request.POST)
        if form.is_valid():
            try:
                teacher = TeacherService.create_teacher(
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    email=form.cleaned_data["email"],
                    contact=form.cleaned_data["contact"],
                    password=form.cleaned_data.get("password1"),
                )
                messages.success(
                    request, f"Teacher '{teacher}' added successfully."
                )
                return HttpResponseRedirect(
                    reverse_lazy("auth_core:teacher_detail", kwargs={"pk": teacher.pk})
                )
            except ValidationError as e:
                form.add_error(None, e)

        return self.render_to_response(self.get_context_data(form=form))


class TeacherUpdateView(AdminRequiredMixin, TemplateView):
    """
    Renders edit form and handles teacher profile updates.
    - Admin only.
    """

    template_name = "auth_core/teachers/teacher_form.html"

    def get_teacher(self):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(Teacher, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        teacher = self.get_teacher()
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get(
            "form", TeacherForm(teacher_instance=teacher)
        )
        context["teacher"] = teacher
        context["page_title"] = "Edit Teacher"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Teachers", "url": reverse_lazy("auth_core:teacher_list")},
            {"label": str(teacher), "url": reverse_lazy("auth_core:teacher_detail", kwargs={"pk": teacher.pk})},
            {"label": "Edit", "url": None},
        ]
        return context

    def get(self, request, *args, **kwargs):
        teacher = self.get_teacher()
        form = TeacherForm(teacher_instance=teacher)
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        teacher = self.get_teacher()
        form = TeacherForm(request.POST, teacher_instance=teacher)
        if form.is_valid():
            try:
                updated = TeacherService.update_teacher(
                    teacher=teacher,
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                    email=form.cleaned_data["email"],
                    contact=form.cleaned_data["contact"],
                    password=form.cleaned_data.get("password1"),
                )
                messages.success(
                    request, f"Teacher '{updated}' updated successfully."
                )
                return HttpResponseRedirect(
                    reverse_lazy("auth_core:teacher_detail", kwargs={"pk": updated.pk})
                )
            except ValidationError as e:
                form.add_error(None, e)

        return self.render_to_response(self.get_context_data(form=form))


class TeacherDeactivateView(AdminRequiredMixin, View):
    """
    Soft-deactivates a teacher by setting user.is_active = False via POST.
    - Admin only.
    - Does not hard-delete: preserves classrooms, attendance history, relationships.
    """

    def post(self, request, *args, **kwargs):
        from django.shortcuts import get_object_or_404
        teacher = get_object_or_404(Teacher, pk=self.kwargs["pk"])
        try:
            TeacherService.deactivate_teacher(teacher)
            messages.success(
                request,
                f"Teacher '{teacher}' has been deactivated. Their account is now inactive.",
            )
        except Exception as e:
            messages.error(request, str(e))
        return HttpResponseRedirect(reverse_lazy("auth_core:teacher_list"))
