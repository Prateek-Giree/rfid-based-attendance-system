from unfold.admin import ModelAdmin
from django.contrib.admin import register
from .models import Classroom, Student


@register(Classroom)
class ClassroomAdmin(ModelAdmin):
    list_display = (
        "name",
        "section",
        "class_teacher",
    )

    search_fields = (
        "name",
        "section",
    )

    list_filter = ("section",)

    ordering = (
        "name",
        "section",
    )


@register(Student)
class StudentAdmin(ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "roll_no",
        "classroom",
        "rfid_uid",
    )

    search_fields = (
        "first_name",
        "last_name",
        "roll_no",
        "rfid_uid",
    )

    list_filter = ("classroom",)

    ordering = (
        "classroom",
        "roll_no",
    )

    list_per_page = 20
