from django.db import models
from apps.students.models import Student


class Attendance(models.Model):

    STATUS_CHOICES = [
        ("present", "Present"),
        ("late", "Late"),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField(db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="present")

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"], name="one_attendance_per_day"
            )
        ]

        indexes = [
            models.Index(fields=["student", "date"]),
        ]

    def __str__(self):
        return f"{self.student.first_name} {self.student.last_name} - {self.date}"
