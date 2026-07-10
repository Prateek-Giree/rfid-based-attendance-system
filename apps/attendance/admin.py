from .models import Attendance
from unfold.admin import ModelAdmin
from django.contrib.admin import register

@register(Attendance)
class AttendanceAdmin(ModelAdmin):
    list_display = (
        "id",
        "student",
        "date",
        "status",
        "timestamp",
    )

    search_fields = (
        "student__name",
        "student__rfid_uid",
    )

    list_filter = (
        "date",
        "status",
    )

    ordering = (
        "-date",
        "-timestamp",
    )