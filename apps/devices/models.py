from django.db import models
from secrets import token_hex


class RFIDDevice(models.Model):
    name = models.CharField(max_length=100)

    classroom = models.ForeignKey(
        "students.Classroom",
        on_delete=models.CASCADE,
        related_name="devices",
    )

    api_key = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )

    is_active = models.BooleanField(default=True)

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = token_hex(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name    
    
    
class RFIDScanLog(models.Model):
    device = models.ForeignKey(
        RFIDDevice,
        on_delete=models.CASCADE,
        related_name="scan_logs",
    )

    uid = models.CharField(max_length=50)

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    success = models.BooleanField(default=False)

    message = models.CharField(max_length=255)

    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scanned_at"]