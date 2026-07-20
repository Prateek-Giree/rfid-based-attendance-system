import datetime
from django.db.models import Count, Q
from django.utils import timezone
from apps.attendance.models import Attendance
from apps.students.models import Student, Classroom
from apps.auth_core.models import Teacher
from apps.devices.models import RFIDDevice, RFIDScanLog
from django.db.models import Exists, OuterRef

class AnalyticsService:
    @staticmethod
    def get_attendance_trend_data(user, days=7, classroom_id=None):
        """
        Returns daily attendance counts (present) for the last `days` days.
        Role-aware and filterable by classroom.
        """
        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=days - 1)

        qs = Attendance.objects.filter(date__range=[start_date, today], status="present")

        if user.is_staff:
            if classroom_id:
                qs = qs.filter(student__classroom_id=classroom_id)
        elif hasattr(user, "teacher_profile"):
            teacher = user.teacher_profile
            qs = qs.filter(student__classroom__class_teacher=teacher)
            if classroom_id:
                # Ensure teacher owns the classroom
                try:
                    c = Classroom.objects.get(id=classroom_id, class_teacher=teacher)
                    qs = qs.filter(student__classroom=c)
                except Classroom.DoesNotExist:
                    qs = qs.none()
        else:
            qs = qs.none()

        # Group by date
        counts = qs.values("date").annotate(count=Count("id")).order_by("date")
        
        # Fill in missing dates
        data_map = {item["date"]: item["count"] for item in counts}
        labels = []
        data = []
        for i in range(days):
            d = start_date + datetime.timedelta(days=i)
            labels.append(d.strftime("%b %d"))
            data.append(data_map.get(d, 0))

        return {"labels": labels, "data": data}

    @staticmethod
    def get_present_vs_absent_data(user, date=None, classroom_id=None):
        """
        Returns pie chart data for Present, Late, and Absent.
        """
        if date is None:
            date = timezone.localdate()

        qs = Attendance.objects.filter(date=date)
        students_qs = Student.objects.filter(is_active=True)

        if user.is_staff:
            if classroom_id:
                qs = qs.filter(student__classroom_id=classroom_id)
                students_qs = students_qs.filter(classroom_id=classroom_id)
        elif hasattr(user, "teacher_profile"):
            teacher = user.teacher_profile
            qs = qs.filter(student__classroom__class_teacher=teacher)
            students_qs = students_qs.filter(classroom__class_teacher=teacher)
            if classroom_id:
                try:
                    c = Classroom.objects.get(id=classroom_id, class_teacher=teacher)
                    qs = qs.filter(student__classroom=c)
                    students_qs = students_qs.filter(classroom=c)
                except Classroom.DoesNotExist:
                    qs = qs.none()
                    students_qs = students_qs.none()
        else:
            qs = qs.none()
            students_qs = students_qs.none()

        present_count = qs.filter(status="present").count()
        late_count = qs.filter(status="late").count()
        total_students = students_qs.count()
        absent_count = max(total_students - (present_count + late_count), 0)

        return {
            "labels": ["Present", "Late", "Absent"],
            "data": [present_count, late_count, absent_count],
            "colors": ["#10B981", "#F59E0B", "#EF4444"]
        }

    @staticmethod
    def get_classroom_comparison_data(user, date=None):
        """
        Returns attendance rates by classroom for a specific date.
        """
        if date is None:
            date = timezone.localdate()

        classrooms_qs = Classroom.objects.all().order_by("name")
        if not user.is_staff and hasattr(user, "teacher_profile"):
            classrooms_qs = classrooms_qs.filter(class_teacher=user.teacher_profile)
        elif not user.is_staff:
            classrooms_qs = classrooms_qs.none()

        labels = []
        data = []

        for c in classrooms_qs:
            total = Student.objects.filter(classroom=c, is_active=True).count()
            if total == 0:
                continue
            present_late = Attendance.objects.filter(
                student__classroom=c, date=date
            ).count() # present or late
            
            rate = round((present_late / total) * 100, 1)
            labels.append(f"{c.name} {c.section}")
            data.append(rate)

        return {"labels": labels, "data": data}

    @staticmethod
    def get_student_growth_trend(user, days=30):
        """
        Line chart: Student registration growth over time.
        """
        if not user.is_staff:
            return {"labels": [], "data": []}

        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=days - 1)
        
        qs = Student.objects.filter(created_at__date__range=[start_date, today])
        counts = qs.values("created_at__date").annotate(count=Count("id")).order_by("created_at__date")
        
        data_map = {item["created_at__date"]: item["count"] for item in counts}
        labels = []
        data = []
        
        # Accumulate total to show growth, or just daily added. Let's do daily added.
        for i in range(days):
            d = start_date + datetime.timedelta(days=i)
            labels.append(d.strftime("%b %d"))
            data.append(data_map.get(d, 0))
            
        return {"labels": labels, "data": data}

    @staticmethod
    def get_student_distribution_data(user):
        """
        Doughnut chart: Students per classroom.
        """
        if user.is_staff:
            classrooms_qs = Classroom.objects.all()
        elif hasattr(user, "teacher_profile"):
            classrooms_qs = Classroom.objects.filter(class_teacher=user.teacher_profile)
        else:
            return {"labels": [], "data": []}

        data_map = classrooms_qs.annotate(
            student_count=Count("students", filter=Q(students__is_active=True))
        ).values("name", "section", "student_count").order_by("name", "section")

        labels = []
        data = []
        # Pre-defined nice colors
        colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16']
        chart_colors = []

        for idx, item in enumerate(data_map):
            if item["student_count"] > 0:
                labels.append(f"{item['name']} {item['section']}")
                data.append(item["student_count"])
                chart_colors.append(colors[idx % len(colors)])

        return {"labels": labels, "data": data, "colors": chart_colors}

    @staticmethod
    def get_teacher_distribution_data(user):
        """
        Bar chart: Teachers assigned per classroom.
        """
        if not user.is_staff:
            return {"labels": [], "data": []}

        # Count how many classrooms each teacher has, or list classrooms and their teacher.
        # Requirements: "Teachers assigned per classroom". Usually it's 1 teacher per classroom in this schema.
        # Maybe show number of students per teacher? The requirement says "Teachers assigned per classroom".
        # Since class_teacher is a ForeignKey on Classroom, it's 1 per classroom. This might mean "Number of classrooms per teacher".
        # Let's count classrooms per teacher.
        teachers = Teacher.objects.filter(user__is_active=True).annotate(
            classroom_count=Count('classrooms')
        ).filter(classroom_count__gt=0).order_by('-classroom_count')

        labels = []
        data = []
        for t in teachers:
            labels.append(f"{t.user.first_name} {t.user.last_name}")
            data.append(t.classroom_count)

        return {"labels": labels, "data": data}

    @staticmethod
    def get_device_status_breakdown(user):
        """
        Doughnut chart: Active vs Offline vs Disabled devices.
        """
        if not user.is_staff:
            return {"labels": [], "data": [], "colors": []}

        threshold = timezone.now() - datetime.timedelta(minutes=15)
        devices = RFIDDevice.objects.all()
        
        disabled = devices.filter(is_active=False).count()
        active = devices.filter(is_active=True, last_seen__gte=threshold).count()
        offline = devices.filter(is_active=True).filter(
            Q(last_seen__isnull=True) | Q(last_seen__lt=threshold)
        ).count()

        return {
            "labels": ["Active", "Offline", "Disabled"],
            "data": [active, offline, disabled],
            "colors": ["#10B981", "#F59E0B", "#EF4444"]
        }

    @staticmethod
    def get_attendance_source_breakdown(user, days=30):
        """
        Doughnut chart: RFID vs Manual attendance (last 30 days).
        """
        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=days - 1)
        
        qs = Attendance.objects.filter(date__range=[start_date, today])
        
        if hasattr(user, "teacher_profile") and not user.is_staff:
            qs = qs.filter(student__classroom__class_teacher=user.teacher_profile)
        elif not user.is_staff:
            return {"labels": [], "data": [], "colors": []}

        scan_log_subquery = RFIDScanLog.objects.filter(
            student=OuterRef('student'),
            scanned_at__date=OuterRef('date'),
            success=True
        )
        qs = qs.annotate(is_rfid=Exists(scan_log_subquery))
        
        rfid_count = qs.filter(is_rfid=True).count()
        manual_count = qs.filter(is_rfid=False).count()
        
        return {
            "labels": ["RFID", "Manual"],
            "data": [rfid_count, manual_count],
            "colors": ["#6366F1", "#94A3B8"]
        }

    @staticmethod
    def get_monthly_attendance_trend(user, days=30):
        """
        Line chart: Attendance percentage by day (last 30 days).
        """
        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=days - 1)
        
        qs = Attendance.objects.filter(date__range=[start_date, today])
        students_qs = Student.objects.filter(is_active=True)
        
        if hasattr(user, "teacher_profile") and not user.is_staff:
            teacher = user.teacher_profile
            qs = qs.filter(student__classroom__class_teacher=teacher)
            students_qs = students_qs.filter(classroom__class_teacher=teacher)
        elif not user.is_staff:
            return {"labels": [], "data": []}

        total_students = students_qs.count()
        if total_students == 0:
             return {"labels": [], "data": []}

        # Present or Late
        counts = qs.filter(status__in=["present", "late"]).values("date").annotate(count=Count("id")).order_by("date")
        data_map = {item["date"]: item["count"] for item in counts}
        
        labels = []
        data = []
        
        for i in range(days):
            d = start_date + datetime.timedelta(days=i)
            labels.append(d.strftime("%b %d"))
            
            present_count = data_map.get(d, 0)
            rate = round((present_count / total_students) * 100, 1)
            data.append(rate)
            
        return {"labels": labels, "data": data}

    # ------------------------------------------------------------------ #
    # Phase 7.5 — Advanced Analytics                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_student_registration_trend(user, days=30, classroom_id=None):
        """
        Line chart: Daily student registrations over the last `days` days.
        Admin-only. Optionally filtered by classroom.
        """
        if not user.is_staff:
            return {"labels": [], "data": []}

        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=days - 1)

        qs = Student.objects.filter(created_at__date__range=[start_date, today])
        if classroom_id:
            qs = qs.filter(classroom_id=classroom_id)

        counts = qs.values("created_at__date").annotate(count=Count("id")).order_by("created_at__date")
        data_map = {item["created_at__date"]: item["count"] for item in counts}

        labels = []
        data = []
        for i in range(days):
            d = start_date + datetime.timedelta(days=i)
            labels.append(d.strftime("%b %d"))
            data.append(data_map.get(d, 0))

        return {"labels": labels, "data": data}

    @staticmethod
    def _compute_attendance_percentages(user, classroom_id=None):
        """
        Internal helper: returns a queryset of students annotated with
        total_records and present_late_count, filtered by role.
        """
        from django.db.models import FloatField, ExpressionWrapper
        students_qs = Student.objects.filter(is_active=True)

        if user.is_staff:
            if classroom_id:
                students_qs = students_qs.filter(classroom_id=classroom_id)
        elif hasattr(user, "teacher_profile"):
            teacher = user.teacher_profile
            students_qs = students_qs.filter(classroom__class_teacher=teacher)
            if classroom_id:
                try:
                    c = Classroom.objects.get(id=classroom_id, class_teacher=teacher)
                    students_qs = students_qs.filter(classroom=c)
                except Classroom.DoesNotExist:
                    return Student.objects.none()
        else:
            return Student.objects.none()

        students_qs = students_qs.annotate(
            total_records=Count("attendance_records"),
            present_late_count=Count(
                "attendance_records",
                filter=Q(attendance_records__status__in=["present", "late"])
            )
        )
        return students_qs

    @staticmethod
    def get_top_defaulters(user, limit=10, classroom_id=None):
        """
        Horizontal bar chart: Students with the lowest attendance percentage.
        Returns ascending sort (worst first).
        """
        from django.db.models import FloatField, ExpressionWrapper, Case, When, Value
        students_qs = AnalyticsService._compute_attendance_percentages(user, classroom_id)

        # Only include students with at least 1 attendance record to avoid division by zero
        students_qs = students_qs.filter(total_records__gt=0)

        # Compute percentage as an annotated float expression
        students_list = list(
            students_qs.values("first_name", "last_name", "total_records", "present_late_count")
        )

        # Sort by attendance percentage ascending (lowest first)
        def pct(s):
            return round((s["present_late_count"] / s["total_records"]) * 100, 1) if s["total_records"] else 0

        students_list.sort(key=pct)
        students_list = students_list[:limit]

        labels = [f"{s['first_name']} {s['last_name']}" for s in students_list]
        data = [pct(s) for s in students_list]

        return {"labels": labels, "data": data}

    @staticmethod
    def get_top_regular_students(user, limit=10, classroom_id=None):
        """
        Horizontal bar chart: Students with the highest attendance percentage.
        Returns descending sort (best first).
        """
        students_qs = AnalyticsService._compute_attendance_percentages(user, classroom_id)
        students_qs = students_qs.filter(total_records__gt=0)

        students_list = list(
            students_qs.values("first_name", "last_name", "total_records", "present_late_count")
        )

        def pct(s):
            return round((s["present_late_count"] / s["total_records"]) * 100, 1) if s["total_records"] else 0

        students_list.sort(key=pct, reverse=True)
        students_list = students_list[:limit]

        labels = [f"{s['first_name']} {s['last_name']}" for s in students_list]
        data = [pct(s) for s in students_list]

        return {"labels": labels, "data": data}

    @staticmethod
    def get_attendance_heatmap_data(user, classroom_id=None):
        """
        GitHub-style heatmap: daily attendance counts for the last 365 days.
        Returns a list of {date, count, level} dicts for each day.
        level: 0 = none, 1 = low, 2 = mid-low, 3 = mid-high, 4 = high.
        """
        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=364)

        qs = Attendance.objects.filter(date__range=[start_date, today])

        if user.is_staff:
            if classroom_id:
                qs = qs.filter(student__classroom_id=classroom_id)
        elif hasattr(user, "teacher_profile"):
            teacher = user.teacher_profile
            qs = qs.filter(student__classroom__class_teacher=teacher)
            if classroom_id:
                try:
                    c = Classroom.objects.get(id=classroom_id, class_teacher=teacher)
                    qs = qs.filter(student__classroom=c)
                except Classroom.DoesNotExist:
                    qs = qs.none()
        else:
            qs = qs.none()

        counts = qs.values("date").annotate(count=Count("id")).order_by("date")
        data_map = {item["date"]: item["count"] for item in counts}

        if data_map:
            max_count = max(data_map.values()) or 1
        else:
            max_count = 1

        cells = []
        for i in range(365):
            d = start_date + datetime.timedelta(days=i)
            count = data_map.get(d, 0)
            if count == 0:
                level = 0
            elif count <= max_count * 0.25:
                level = 1
            elif count <= max_count * 0.50:
                level = 2
            elif count <= max_count * 0.75:
                level = 3
            else:
                level = 4
            cells.append({"date": d.strftime("%Y-%m-%d"), "label": d.strftime("%b %d, %Y"), "count": count, "level": level})

        return {"cells": cells, "max_count": max_count}

    @staticmethod
    def get_rfid_scan_activity(user, days=30):
        """
        Line chart: RFID scans per day (total, successful, failed).
        Admin-only.
        """
        if not user.is_staff:
            return {"labels": [], "total": [], "successful": [], "failed": []}

        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=days - 1)

        qs = RFIDScanLog.objects.filter(scanned_at__date__range=[start_date, today])

        total_counts = (
            qs.values("scanned_at__date")
            .annotate(count=Count("id"))
            .order_by("scanned_at__date")
        )
        success_counts = (
            qs.filter(success=True)
            .values("scanned_at__date")
            .annotate(count=Count("id"))
            .order_by("scanned_at__date")
        )
        fail_counts = (
            qs.filter(success=False)
            .values("scanned_at__date")
            .annotate(count=Count("id"))
            .order_by("scanned_at__date")
        )

        total_map = {item["scanned_at__date"]: item["count"] for item in total_counts}
        success_map = {item["scanned_at__date"]: item["count"] for item in success_counts}
        fail_map = {item["scanned_at__date"]: item["count"] for item in fail_counts}

        labels = []
        total = []
        successful = []
        failed = []

        for i in range(days):
            d = start_date + datetime.timedelta(days=i)
            labels.append(d.strftime("%b %d"))
            total.append(total_map.get(d, 0))
            successful.append(success_map.get(d, 0))
            failed.append(fail_map.get(d, 0))

        return {"labels": labels, "total": total, "successful": successful, "failed": failed}

    @staticmethod
    def get_monthly_attendance_comparison(user, months=6, classroom_id=None):
        """
        Grouped bar chart: Present, Late, Absent counts per month for the last `months` months.
        """
        from django.db.models.functions import TruncMonth

        today = timezone.localdate()
        # Start from beginning of month `months` ago
        start_month = (today.replace(day=1) - datetime.timedelta(days=(months - 1) * 30)).replace(day=1)

        qs = Attendance.objects.filter(date__gte=start_month)
        students_qs = Student.objects.filter(is_active=True)

        if user.is_staff:
            if classroom_id:
                qs = qs.filter(student__classroom_id=classroom_id)
                students_qs = students_qs.filter(classroom_id=classroom_id)
        elif hasattr(user, "teacher_profile"):
            teacher = user.teacher_profile
            qs = qs.filter(student__classroom__class_teacher=teacher)
            students_qs = students_qs.filter(classroom__class_teacher=teacher)
            if classroom_id:
                try:
                    c = Classroom.objects.get(id=classroom_id, class_teacher=teacher)
                    qs = qs.filter(student__classroom=c)
                    students_qs = students_qs.filter(classroom=c)
                except Classroom.DoesNotExist:
                    qs = qs.none()
                    students_qs = students_qs.none()
        else:
            qs = qs.none()
            students_qs = students_qs.none()

        present_counts = (
            qs.filter(status="present")
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        late_counts = (
            qs.filter(status="late")
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
 
        present_map = {item["month"]: item["count"] for item in present_counts}
        late_map = {item["month"]: item["count"] for item in late_counts}

        total_students = students_qs.count()

        labels = []
        present_data = []
        late_data = []
        absent_data = []

        for i in range(months):
            month_start = (start_month.replace(day=1) + datetime.timedelta(days=i * 31)).replace(day=1)
            # Determine working days in that month (days in month)
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1, day=1)
            days_in_month = (next_month - month_start).days

            label = month_start.strftime("%b %Y")
            p = present_map.get(month_start, 0)
            l = late_map.get(month_start, 0)
            # Absent = total capacity - (present + late)
            capacity = total_students * days_in_month
            a = max(capacity - p - l, 0)

            labels.append(label)
            present_data.append(p)
            late_data.append(l)
            absent_data.append(a)

        return {"labels": labels, "present": present_data, "late": late_data, "absent": absent_data}

    @staticmethod
    def get_attendance_source_comparison(user, days=30, classroom_id=None):
        """
        Doughnut chart: RFID vs Manual attendance.
        RFID = matching RFIDScanLog exists; Manual = no matching log.
        """
        today = timezone.localdate()
        start_date = today - datetime.timedelta(days=days - 1)

        qs = Attendance.objects.filter(date__range=[start_date, today])

        if user.is_staff:
            if classroom_id:
                qs = qs.filter(student__classroom_id=classroom_id)
        elif hasattr(user, "teacher_profile"):
            teacher = user.teacher_profile
            qs = qs.filter(student__classroom__class_teacher=teacher)
            if classroom_id:
                try:
                    c = Classroom.objects.get(id=classroom_id, class_teacher=teacher)
                    qs = qs.filter(student__classroom=c)
                except Classroom.DoesNotExist:
                    qs = qs.none()
        else:
            return {"labels": [], "data": [], "colors": []}

        scan_log_subquery = RFIDScanLog.objects.filter(
            student=OuterRef("student"),
            scanned_at__date=OuterRef("date"),
            success=True,
        )
        qs = qs.annotate(is_rfid=Exists(scan_log_subquery))

        rfid_count = qs.filter(is_rfid=True).count()
        manual_count = qs.filter(is_rfid=False).count()

        return {
            "labels": ["RFID", "Manual"],
            "data": [rfid_count, manual_count],
            "colors": ["#6366F1", "#94A3B8"],
        }
