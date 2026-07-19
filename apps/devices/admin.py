from django.contrib import admin
from .models import RFIDDevice, RFIDScanLog
# Register your models here.

admin.site.register(RFIDDevice)
admin.site.register(RFIDScanLog)