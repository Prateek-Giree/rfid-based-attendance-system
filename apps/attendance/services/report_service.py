import csv
import datetime
from django.http import HttpResponse
from django.db.models import Exists, OuterRef
from apps.attendance.models import Attendance
from apps.students.models import Classroom
from apps.devices.models import RFIDScanLog

class ReportService:
    @staticmethod
    def get_report_data(user, start_date_str, end_date_str, classroom_id, source=None):
        """
        Returns an annotated queryset of Attendance records.
        """
        qs = Attendance.objects.select_related("student", "student__classroom").order_by("-date", "-timestamp")

        # Base role filtering
        if hasattr(user, "teacher_profile") and not user.is_staff:
            qs = qs.filter(student__classroom__class_teacher=user.teacher_profile)
        elif not user.is_staff:
            return Attendance.objects.none()

        # Date range filtering
        if start_date_str:
            try:
                start = datetime.date.fromisoformat(start_date_str)
                qs = qs.filter(date__gte=start)
            except ValueError:
                pass
        if end_date_str:
            try:
                end = datetime.date.fromisoformat(end_date_str)
                qs = qs.filter(date__lte=end)
            except ValueError:
                pass

        # Classroom filtering
        if classroom_id:
            qs = qs.filter(student__classroom_id=classroom_id)

        # Annotate with source (RFID vs Manual)
        # If an RFIDScanLog exists for this student on this date with success=True, we assume RFID.
        scan_log_subquery = RFIDScanLog.objects.filter(
            student=OuterRef('student'),
            scanned_at__date=OuterRef('date'),
            success=True
        )
        qs = qs.annotate(is_rfid=Exists(scan_log_subquery))

        # Source filtering
        if source == "rfid":
            qs = qs.filter(is_rfid=True)
        elif source == "manual":
            qs = qs.filter(is_rfid=False)

        return qs

    @staticmethod
    def generate_csv_report(queryset):
        """
        Generates a CSV HttpResponse from an Attendance queryset.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_report_{datetime.date.today().isoformat()}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date', 
            'Student Name', 
            'Roll No', 
            'Classroom', 
            'Status', 
            'Source', 
            'Recorded At'
        ])

        for record in queryset:
            source_text = "RFID" if getattr(record, 'is_rfid', False) else "Manual"
            writer.writerow([
                record.date.isoformat(),
                f"{record.student.first_name} {record.student.last_name}",
                record.student.roll_no,
                f"{record.student.classroom.name} {record.student.classroom.section}",
                record.status.capitalize(),
                source_text,
                record.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            ])

        return response
