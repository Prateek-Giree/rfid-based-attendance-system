from django.db import models


class Classroom(models.Model):
    name = models.CharField(max_length=50)
    section = models.CharField(max_length=10)

    class_teacher = models.ForeignKey(
        "auth_core.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classrooms",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("name", "section")
        ordering = ["name", "section"]

    def __str__(self):
        return f"{self.name} - {self.section}"


class Student(models.Model):
    roll_no = models.PositiveIntegerField()

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="students",
    )

    rfid_uid = models.CharField(
        max_length=50,
        unique=True,
    )

    address = models.TextField(blank=True)

    contact = models.CharField(
        max_length=20,
        blank=True,
    )

    guardian_name = models.CharField(max_length=100)

    guardian_contact = models.CharField(
        max_length=20,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("classroom", "roll_no")
        ordering = ["classroom", "roll_no"]

    def __str__(self):
        return f"{self.roll_no} - {self.first_name} {self.last_name}"
