import datetime
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, View, TemplateView

from apps.core.mixins import AdminRequiredMixin, TeacherRequiredMixin
from apps.students.models import Classroom, Student
from apps.attendance.models import Attendance
from apps.attendance.forms import AttendanceFilterForm, AttendanceMarkForm
from apps.attendance.services.attendance_service import AttendanceService


class AttendanceListView(TeacherRequiredMixin, ListView):
    """
    Paginated list of all attendance records.
    Supports HTMX-driven classroom + date filtering.
    Admin sees all records; Teacher sees their classrooms only.
    """

    model = Attendance
    paginate_by = 20
    context_object_name = "records"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["attendance/partials/attendance_table.html"]
        return ["attendance/attendance_list.html"]

    def get_queryset(self):
        qs = AttendanceService.get_attendance_queryset(self.request.user)
        classroom_id = self.request.GET.get("classroom", "").strip()
        date_str = self.request.GET.get("date", "").strip()
        return AttendanceService.filter_attendance(qs, classroom_id, date_str)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = AttendanceService.get_attendance_stats(self.request.user)
        context.update(stats)

        # Pre-populate filter form with current GET params
        context["filter_form"] = AttendanceFilterForm(self.request.GET or None)
        context["selected_classroom"] = self.request.GET.get("classroom", "")
        context["selected_date"] = self.request.GET.get("date", "")
        context["page_title"] = "Attendance"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Attendance", "url": None},
        ]
        return context


class AttendanceMarkView(TeacherRequiredMixin, View):
    """
    GET  — renders the manual attendance marking page.
            Shows classroom selector + date picker.
            If both are valid, renders the student roster.
    POST — processes bulk attendance submission.
    """

    template_name = "attendance/attendance_mark.html"

    def _check_classroom_permission(self, request, classroom):
        """Raises PermissionDenied if a Teacher tries to access a classroom they don't own."""
        if request.user.is_staff:
            return
        if not hasattr(request.user, "teacher_profile"):
            raise PermissionDenied
        if classroom.class_teacher != request.user.teacher_profile:
            raise PermissionDenied

    def get(self, request, *args, **kwargs):
        form = AttendanceMarkForm(request.GET or None)
        roster = None
        classroom = None
        date = None

        if form.is_valid():
            classroom = form.cleaned_data["classroom"]
            date = form.cleaned_data["date"]
            self._check_classroom_permission(request, classroom)
            roster = AttendanceService.get_classroom_roster(classroom, date)

        return self._render(request, form, roster, classroom, date)

    def post(self, request, *args, **kwargs):
        form = AttendanceMarkForm(request.POST)
        roster = None
        classroom = None
        date = None

        if not form.is_valid():
            return self._render(request, form, roster, classroom, date)

        classroom = form.cleaned_data["classroom"]
        date = form.cleaned_data["date"]
        self._check_classroom_permission(request, classroom)

        # Collect status values from POST: student_<id> = "present"|"late"|"absent"
        student_status_map = {}
        for key, value in request.POST.items():
            if key.startswith("student_") and value in ("present", "late", "absent"):
                student_id = key.replace("student_", "")
                student_status_map[student_id] = value

        try:
            result = AttendanceService.bulk_mark_attendance(
                classroom=classroom,
                date=date,
                student_status_map=student_status_map,
            )
            messages.success(
                request,
                f"Attendance saved — {result['created']} created, "
                f"{result['updated']} updated, {result['skipped']} absent.",
            )
        except Exception as e:
            messages.error(request, str(e))

        return HttpResponseRedirect(
            reverse("attendance:attendance_mark")
            + f"?classroom={classroom.pk}&date={date.isoformat()}"
        )

    def _render(self, request, form, roster, classroom, date):
        from django.shortcuts import render
        context = {
            "form": form,
            "roster": roster,
            "classroom": classroom,
            "date": date,
            "page_title": "Mark Attendance",
            "breadcrumbs": [
                {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
                {"label": "Attendance", "url": reverse_lazy("attendance:attendance_list")},
                {"label": "Mark", "url": None},
            ],
        }
        return render(request, self.template_name, context)


class AttendanceStudentHistoryView(TeacherRequiredMixin, View):
    """
    Shows the complete attendance history for a single student.
    Teachers may only view students in their assigned classrooms.
    """

    template_name = "attendance/student_history.html"

    def get(self, request, *args, **kwargs):
        student = get_object_or_404(Student, pk=self.kwargs["pk"])

        # Role check
        if not request.user.is_staff:
            if not hasattr(request.user, "teacher_profile"):
                raise PermissionDenied
            if student.classroom.class_teacher != request.user.teacher_profile:
                raise PermissionDenied

        records = AttendanceService.get_student_attendance(student, request.user)
        summary = AttendanceService.get_student_attendance_summary(student)

        from django.shortcuts import render
        context = {
            "student": student,
            "records": records,
            "page_title": f"{student.first_name} {student.last_name} — Attendance",
            "breadcrumbs": [
                {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
                {"label": "Attendance", "url": reverse_lazy("attendance:attendance_list")},
                {"label": f"{student.first_name} {student.last_name}", "url": None},
            ],
        }
        context.update(summary)
        return render(request, self.template_name, context)


class AttendanceDeleteView(AdminRequiredMixin, View):
    """
    Hard-deletes a single attendance record.
    Admin only — triggered via SweetAlert2 confirmation.
    """

    def post(self, request, *args, **kwargs):
        record = get_object_or_404(Attendance, pk=self.kwargs["pk"])
        student_name = f"{record.student.first_name} {record.student.last_name}"
        record_date = record.date
        record.delete()
        messages.success(
            request,
            f"Attendance record for {student_name} on {record_date} deleted.",
        )
        return HttpResponseRedirect(reverse_lazy("attendance:attendance_list"))

# ------------------------------------------------------------------ #
# Student Portal (Unauthenticated)                                     #
# ------------------------------------------------------------------ #

class StudentPortalView(TemplateView):
    """
    Renders the public student portal search page.
    """
    template_name = "attendance/portal.html"

class StudentPortalLookupView(View):
    """
    Handles HTMX lookup of a student by RFID UID.
    """
    template_name = "attendance/partials/portal_results.html"

    def get(self, request, *args, **kwargs):
        uid = request.GET.get("uid", "").strip()
        context = {}
        
        if not uid:
            return self._render_error(request, "Please enter an RFID UID.")

        try:
            student = Student.objects.get(rfid_uid__iexact=uid, is_active=True)
            # We don't check user role here because this is public, but we only return their own records.
            records = Attendance.objects.filter(student=student).order_by("-date")[:30] # Limit to recent 30
            summary = AttendanceService.get_student_attendance_summary(student)
            
            context["student"] = student
            context["records"] = records
            context.update(summary)
            
            from django.shortcuts import render
            return render(request, self.template_name, context)

        except Student.DoesNotExist:
            return self._render_error(request, "No active student found with this RFID card.")

    def _render_error(self, request, message):
        from django.shortcuts import render
        return render(request, self.template_name, {"error": message})

# ------------------------------------------------------------------ #
# Reports                                                              #
# ------------------------------------------------------------------ #

class AttendanceReportView(TeacherRequiredMixin, ListView):
    """
    Renders the report page with filters and table.
    """
    template_name = "attendance/report.html"
    context_object_name = "records"
    paginate_by = 50

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["attendance/partials/report_table.html"]
        return [self.template_name]

    def get_queryset(self):
        from apps.attendance.services.report_service import ReportService
        
        start_date = self.request.GET.get("start_date", "")
        end_date = self.request.GET.get("end_date", "")
        classroom_id = self.request.GET.get("classroom", "")
        source = self.request.GET.get("source", "")

        return ReportService.get_report_data(
            user=self.request.user,
            start_date_str=start_date,
            end_date_str=end_date,
            classroom_id=classroom_id,
            source=source
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Determine classrooms based on role
        if self.request.user.is_staff:
            context["classrooms"] = Classroom.objects.all()
        else:
            context["classrooms"] = Classroom.objects.filter(class_teacher=self.request.user.teacher_profile)

        # Retain filter selections
        context["selected_start_date"] = self.request.GET.get("start_date", "")
        context["selected_end_date"] = self.request.GET.get("end_date", "")
        context["selected_classroom"] = self.request.GET.get("classroom", "")
        context["selected_source"] = self.request.GET.get("source", "")

        context["page_title"] = "Attendance Reports"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Reports", "url": None},
        ]
        return context

class AttendanceReportExportView(TeacherRequiredMixin, View):
    """
    Handles CSV export for the attendance report.
    """
    def get(self, request, *args, **kwargs):
        from apps.attendance.services.report_service import ReportService
        
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")
        classroom_id = request.GET.get("classroom", "")
        source = request.GET.get("source", "")

        queryset = ReportService.get_report_data(
            user=request.user,
            start_date_str=start_date,
            end_date_str=end_date,
            classroom_id=classroom_id,
            source=source
        )

        return ReportService.generate_csv_report(queryset)
