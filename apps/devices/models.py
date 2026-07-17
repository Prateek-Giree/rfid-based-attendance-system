from django.db import models

# Create your models here.
class RFIDDevice(models.Model):
    name = models.CharField(max_length=50)

    api_key = models.CharField(
        max_length=64,
        unique=True,
    )

    classroom = models.ForeignKey(
        "students.Classroom",
        on_delete=models.CASCADE,
        related_name="devices",
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
class RFIDScanLog(models.Model):
    device = models.ForeignKey(
        RFIDDevice,
        on_delete=models.CASCADE,
        related_name="scan_logs",
    )

    uid = models.CharField(max_length=50)

    scanned_at = models.DateTimeField(
        auto_now_add=True,
    )

    success = models.BooleanField(default=False)

    message = models.CharField(
        max_length=255,
    )

    class Meta:
        ordering = ["-scanned_at"]