import datetime
from django.db import models, transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.students.models import Classroom, Student
from apps.devices.models import RFIDDevice, RFIDScanLog


class AttendanceService:
    """
    Service layer for Attendance business logic.
    Handles manual marking, bulk marking, history queries, and dashboard statistics.
    All role enforcement is done here — views stay thin.
    """

    # ------------------------------------------------------------------ #
    # Queryset helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_attendance_queryset(user):
        """
        Returns a base Attendance queryset filtered by the caller's role.
        - Admin (is_staff): all records.
        - Teacher: records for students in their assigned classrooms only.
        - Others: empty queryset.
        """
        qs = Attendance.objects.select_related(
            "student", "student__classroom"
        ).order_by("-date", "-timestamp")

        if user.is_staff:
            return qs
        if hasattr(user, "teacher_profile"):
            return qs.filter(
                student__classroom__class_teacher=user.teacher_profile
            )
        return Attendance.objects.none()

    @staticmethod
    def filter_attendance(queryset, classroom_id: str, date_str: str):
        """
        Applies classroom and date filters to an attendance queryset.
        """
        if classroom_id:
            queryset = queryset.filter(student__classroom_id=classroom_id)
        if date_str:
            try:
                parsed = datetime.date.fromisoformat(date_str)
                queryset = queryset.filter(date=parsed)
            except (ValueError, TypeError):
                pass
        return queryset

    # ------------------------------------------------------------------ #
    # Mark attendance                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    @transaction.atomic
    def mark_attendance(student: Student, date: datetime.date, status: str) -> Attendance:
        """
        Creates a single Attendance record.
        Raises ValidationError if a record already exists for student + date.
        """
        if Attendance.objects.filter(student=student, date=date).exists():
            raise ValidationError(
                f"Attendance for {student.first_name} {student.last_name} "
                f"on {date} has already been recorded."
            )
        record = Attendance(student=student, date=date, status=status)
        record.full_clean()
        record.save()
        return record

    @staticmethod
    @transaction.atomic
    def bulk_mark_attendance(classroom: Classroom, date: datetime.date, student_status_map: dict) -> dict:
        """
        Atomically creates or updates Attendance records for an entire classroom
        for a given date.

        student_status_map: {student_id (int): status_str ("present"|"late"|"absent")}
        "absent" means do NOT create a record (or delete existing one).

        Returns:
            created (int): count of newly created records
            updated (int): count of updated records
            skipped (int): count of absent / no-action entries
        """
        created = updated = skipped = 0
        students = Student.objects.filter(
            classroom=classroom, is_active=True
        ).in_bulk()

        for student_id_str, status in student_status_map.items():
            try:
                student_id = int(student_id_str)
            except (ValueError, TypeError):
                continue

            student = students.get(student_id)
            if not student:
                continue

            if status == "absent":
                # Remove existing record if any (allow re-marking as absent)
                Attendance.objects.filter(student=student, date=date).delete()
                skipped += 1
                continue

            record, was_created = Attendance.objects.update_or_create(
                student=student,
                date=date,
                defaults={"status": status},
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return {"created": created, "updated": updated, "skipped": skipped}

    # ------------------------------------------------------------------ #
    # Student history                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_student_attendance(student: Student, user) -> models.QuerySet:
        """
        Returns all Attendance records for a student.
        Teachers may only access students in their assigned classrooms.
        """
        if user.is_staff:
            return Attendance.objects.filter(student=student).order_by("-date")
        if hasattr(user, "teacher_profile"):
            if student.classroom.class_teacher == user.teacher_profile:
                return Attendance.objects.filter(student=student).order_by("-date")
        return Attendance.objects.none()

    @staticmethod
    def get_student_attendance_summary(student: Student) -> dict:
        """
        Computes present/late/absent counts and attendance percentage for a student.
        """
        records = Attendance.objects.filter(student=student)
        total_days = records.count()
        present = records.filter(status="present").count()
        late = records.filter(status="late").count()
        # "Absent" days are not stored — they are the gap between school days and records.
        # We compute the percentage over recorded days only.
        attended = present + late
        percentage = round((attended / total_days) * 100, 1) if total_days else 0

        return {
            "total_days": total_days,
            "present_count": present,
            "late_count": late,
            "absent_count": 0,
            "attendance_percentage": percentage,
        }

    # ------------------------------------------------------------------ #
    # Classroom roster for marking                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_classroom_roster(classroom: Classroom, date: datetime.date) -> list:
        """
        Returns a list of dicts — one per active student in the classroom —
        with their current attendance status for the given date.

        Each dict:
            student: Student instance
            status: "present" | "late" | "absent" (absent if no record)
            record: Attendance instance or None
        """
        students = Student.objects.filter(
            classroom=classroom, is_active=True
        ).order_by("roll_no")

        existing = {
            r.student_id: r
            for r in Attendance.objects.filter(
                student__classroom=classroom, date=date
            )
        }

        roster = []
        for student in students:
            record = existing.get(student.pk)
            roster.append({
                "student": student,
                "status": record.status if record else "absent",
                "record": record,
            })
        return roster

    # ------------------------------------------------------------------ #
    # Dashboard & list statistics                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_attendance_stats(user) -> dict:
        """
        Returns today's attendance statistics for the dashboard.
        Role-aware: Teachers see stats for their classrooms only.
        """
        today = timezone.localdate()

        if user.is_staff:
            today_qs = Attendance.objects.filter(date=today)
            total_students = Student.objects.filter(is_active=True).count()
            total_attendance_records = Attendance.objects.count()
        elif hasattr(user, "teacher_profile"):
            teacher = user.teacher_profile
            today_qs = Attendance.objects.filter(
                date=today,
                student__classroom__class_teacher=teacher,
            )
            total_students = Student.objects.filter(
                classroom__class_teacher=teacher, is_active=True
            ).count()
            total_attendance_records = Attendance.objects.filter(student__classroom__class_teacher=teacher).count()
        else:
            return {
                "today_present": 0,
                "today_late": 0,
                "today_absent": 0,
                "attendance_rate": "—",
                "total_attendance_records": 0,
            }

        today_present = today_qs.filter(status="present").count()
        today_late = today_qs.filter(status="late").count()
        today_marked = today_qs.count()
        today_absent = max(total_students - today_marked, 0)

        rate = (
            round((today_marked / total_students) * 100, 1)
            if total_students
            else 0
        )

        return {
            "today_present": today_present,
            "today_late": today_late,
            "today_absent": today_absent,
            "attendance_rate": f"{rate}%",
            "total_attendance_records": total_attendance_records,
        }

    # ------------------------------------------------------------------ #
    # RFID Processing                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def process_rfid_scan(api_key: str, uid: str) -> dict:
        """
        Processes an RFID scan from a device.
        Validates the device API key, looks up the student by UID,
        and records attendance if not already marked for today.
        Always creates an RFIDScanLog.
        """
        try:
            device = RFIDDevice.objects.get(api_key=api_key, is_active=True)
        except RFIDDevice.DoesNotExist:
            return {"success": False, "message": "Invalid API Key or Device inactive"}

        # Update last seen
        device.last_seen = timezone.now()
        device.save(update_fields=["last_seen"])

        try:
            student = Student.objects.get(rfid_uid__iexact=uid, is_active=True)
        except Student.DoesNotExist:
            RFIDScanLog.objects.create(
                device=device, uid=uid, student=None, success=False, message="Unknown RFID Card"
            )
            return {"success": False, "message": "Unknown RFID Card"}

        today = timezone.localdate()

        # Check for existing attendance today
        if Attendance.objects.filter(student=student, date=today).exists():
            msg = f"Attendance already recorded today for {student.first_name}"
            RFIDScanLog.objects.create(
                device=device, uid=uid, student=student, success=False, message=msg
            )
            return {"success": False, "message": msg}

        # Create attendance
        try:
            with transaction.atomic():
                Attendance.objects.create(student=student, date=today, status="present")
                msg = f"Attendance recorded for {student.first_name}"
                RFIDScanLog.objects.create(
                    device=device, uid=uid, student=student, success=True, message=msg
                )
                return {"success": True, "message": msg}
        except IntegrityError:
            msg = f"Attendance already recorded today for {student.first_name}"
            RFIDScanLog.objects.create(
                device=device, uid=uid, student=student, success=False, message=msg
            )
            return {"success": False, "message": msg}
