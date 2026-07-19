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
