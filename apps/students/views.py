from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.core.mixins import AdminRequiredMixin, TeacherRequiredMixin
from .forms import ClassroomForm, StudentForm
from .models import Classroom, Student
from .services import ClassroomService, StudentService


# ── CLASSROOM VIEWS ───────────────────────────────────────────────────────────

class ClassroomListView(TeacherRequiredMixin, ListView):
    """
    Renders list of classrooms.
    - Admins see all classrooms.
    - Teachers see only their assigned classrooms.
    - Supports live searching via HTMX partial updates.
    """
    model = Classroom
    paginate_by = 10
    context_object_name = "classrooms"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["students/partials/classroom_table.html"]
        return ["students/classroom_list.html"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            queryset = Classroom.objects.all()
        elif hasattr(user, "teacher_profile"):
            queryset = Classroom.objects.filter(class_teacher=user.teacher_profile)
        else:
            queryset = Classroom.objects.none()

        # Select teacher profile and user to prevent N+1 queries,
        # and annotate student counts.
        queryset = queryset.select_related("class_teacher__user").annotate(
            student_count=models.Count("students")
        )

        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                models.Q(name__icontains=q) |
                models.Q(section__icontains=q) |
                models.Q(class_teacher__user__first_name__icontains=q) |
                models.Q(class_teacher__user__last_name__icontains=q) |
                models.Q(class_teacher__user__email__icontains=q)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Classrooms"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Classrooms", "url": None},
        ]
        context["q"] = self.request.GET.get("q", "").strip()
        return context


class ClassroomDetailView(TeacherRequiredMixin, DetailView):
    """
    Renders detailed information for a specific classroom.
    - Admins can view any classroom.
    - Teachers can only view the classroom if assigned as the class teacher.
    """
    model = Classroom
    context_object_name = "classroom"
    template_name = "students/classroom_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.is_staff:
            return obj
        
        if hasattr(user, "teacher_profile") and obj.class_teacher == user.teacher_profile:
            return obj
            
        raise PermissionDenied("You do not have permission to view this classroom.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["students"] = self.object.students.all()
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Classrooms", "url": reverse_lazy("students:classroom_list")},
            {"label": self.object, "url": None},
        ]
        return context


class ClassroomCreateView(AdminRequiredMixin, CreateView):
    """
    Renders creation form and handles classroom creation via the service layer.
    - Admin only.
    """
    model = Classroom
    form_class = ClassroomForm
    template_name = "students/classroom_form.html"
    success_url = reverse_lazy("students:classroom_list")

    def form_valid(self, form):
        try:
            self.object = ClassroomService.create_classroom(
                name=form.cleaned_data["name"],
                section=form.cleaned_data["section"],
                class_teacher=form.cleaned_data["class_teacher"],
            )
            messages.success(self.request, f"Classroom '{self.object}' created successfully.")
            return HttpResponseRedirect(self.get_success_url())
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create Classroom"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Classrooms", "url": reverse_lazy("students:classroom_list")},
            {"label": "Create", "url": None},
        ]
        return context


class ClassroomUpdateView(AdminRequiredMixin, UpdateView):
    """
    Renders edit form and handles classroom updates via the service layer.
    - Admin only.
    """
    model = Classroom
    form_class = ClassroomForm
    template_name = "students/classroom_form.html"
    success_url = reverse_lazy("students:classroom_list")

    def form_valid(self, form):
        try:
            self.object = ClassroomService.update_classroom(
                classroom=self.get_object(),
                name=form.cleaned_data["name"],
                section=form.cleaned_data["section"],
                class_teacher=form.cleaned_data["class_teacher"],
            )
            messages.success(self.request, f"Classroom '{self.object}' updated successfully.")
            return HttpResponseRedirect(self.get_success_url())
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Edit Classroom"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Classrooms", "url": reverse_lazy("students:classroom_list")},
            {"label": "Edit", "url": None},
        ]
        return context


class ClassroomDeleteView(AdminRequiredMixin, DeleteView):
    """
    Deletes classroom via the service layer.
    - Admin only.
    - Enforces deletion checks (prevents deleting if classroom has students or devices).
    """
    model = Classroom
    success_url = reverse_lazy("students:classroom_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            ClassroomService.delete_classroom(self.object)
            messages.success(request, f"Classroom '{self.object}' deleted successfully.")
        except ValidationError as e:
            messages.error(request, e.message)
        return HttpResponseRedirect(self.get_success_url())


# ── STUDENT VIEWS ─────────────────────────────────────────────────────────────

class StudentListView(TeacherRequiredMixin, ListView):
    """
    Renders list of students.
    - Admins see all students.
    - Teachers see only students belonging to their assigned classroom(s).
    - Supports live searching & classroom filtering via HTMX.
    """
    model = Student
    paginate_by = 10
    context_object_name = "students"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["students/partials/student_table.html"]
        return ["students/student_list.html"]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            queryset = Student.objects.all()
        elif hasattr(user, "teacher_profile"):
            queryset = Student.objects.filter(classroom__class_teacher=user.teacher_profile)
        else:
            queryset = Student.objects.none()

        queryset = queryset.select_related("classroom")

        q = self.request.GET.get("q", "").strip()
        classroom_id = self.request.GET.get("classroom", "")
        status_filter = self.request.GET.get("status", "active")

        queryset = StudentService.filter_by_status(queryset, status_filter)
        queryset = StudentService.search_students(queryset, q)
        queryset = StudentService.filter_students(queryset, classroom_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_staff:
            context["classrooms"] = Classroom.objects.all()
        elif hasattr(user, "teacher_profile"):
            context["classrooms"] = Classroom.objects.filter(class_teacher=user.teacher_profile)
        else:
            context["classrooms"] = Classroom.objects.none()

        context["page_title"] = "Students"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Students", "url": None},
        ]
        context["q"] = self.request.GET.get("q", "").strip()
        context["selected_classroom"] = self.request.GET.get("classroom", "")
        context["selected_status"] = self.request.GET.get("status", "active")
        return context


class StudentDetailView(TeacherRequiredMixin, DetailView):
    """
    Renders detailed profile of a student.
    - Admins see any student profile.
    - Teachers see only students in their assigned classroom(s).
    """
    model = Student
    context_object_name = "student"
    template_name = "students/student_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.is_staff:
            return obj
        
        if hasattr(user, "teacher_profile") and obj.classroom.class_teacher == user.teacher_profile:
            return obj
            
        raise PermissionDenied("You do not have permission to view this student's profile.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Students", "url": reverse_lazy("students:student_list")},
            {"label": f"{self.object.first_name} {self.object.last_name}", "url": None},
        ]
        return context


class StudentCreateView(AdminRequiredMixin, CreateView):
    """
    Handles student registration.
    - Admin only.
    """
    model = Student
    form_class = StudentForm
    template_name = "students/student_form.html"
    success_url = reverse_lazy("students:student_list")

    def form_valid(self, form):
        try:
            self.object = StudentService.create_student(
                roll_no=form.cleaned_data["roll_no"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                classroom=form.cleaned_data["classroom"],
                rfid_uid=form.cleaned_data["rfid_uid"],
                guardian_name=form.cleaned_data["guardian_name"],
                address=form.cleaned_data["address"],
                contact=form.cleaned_data["contact"],
                guardian_contact=form.cleaned_data["guardian_contact"],
                is_active=form.cleaned_data["is_active"],
            )
            messages.success(self.request, f"Student '{self.object}' registered successfully.")
            return HttpResponseRedirect(self.get_success_url())
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Register Student"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Students", "url": reverse_lazy("students:student_list")},
            {"label": "Register", "url": None},
        ]
        return context


class StudentUpdateView(AdminRequiredMixin, UpdateView):
    """
    Handles student details updates.
    - Admin only.
    """
    model = Student
    form_class = StudentForm
    template_name = "students/student_form.html"
    success_url = reverse_lazy("students:student_list")

    def form_valid(self, form):
        try:
            self.object = StudentService.update_student(
                student=self.get_object(),
                roll_no=form.cleaned_data["roll_no"],
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                classroom=form.cleaned_data["classroom"],
                rfid_uid=form.cleaned_data["rfid_uid"],
                guardian_name=form.cleaned_data["guardian_name"],
                address=form.cleaned_data["address"],
                contact=form.cleaned_data["contact"],
                guardian_contact=form.cleaned_data["guardian_contact"],
                is_active=form.cleaned_data["is_active"],
            )
            messages.success(self.request, f"Student '{self.object}' updated successfully.")
            return HttpResponseRedirect(self.get_success_url())
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Edit Student"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Students", "url": reverse_lazy("students:student_list")},
            {"label": "Edit", "url": None},
        ]
        return context


class StudentDeleteView(AdminRequiredMixin, DeleteView):
    """
    Deactivates student profile (soft-delete).
    - Admin only.
    """
    model = Student
    success_url = reverse_lazy("students:student_list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            StudentService.delete_student(self.object)
            messages.success(request, f"Student '{self.object}' soft-deleted (marked inactive) successfully.")
        except Exception as e:
            messages.error(request, str(e))
        return HttpResponseRedirect(self.get_success_url())
