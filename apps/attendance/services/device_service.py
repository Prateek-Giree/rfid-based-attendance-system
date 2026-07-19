import datetime
from django.db import models
from django.utils import timezone
from apps.devices.models import RFIDDevice


class DeviceService:
    """
    Service layer containing business logic for RFID Device management.
    Ensures thin views and proper separation of concerns.
    """

    @staticmethod
    def search_devices(queryset, q: str):
        """
        Filters devices queryset by query string q across fields:
        name, api_key, and classroom name/section.
        """
        if not q:
            return queryset
        return queryset.filter(
            models.Q(name__icontains=q) |
            models.Q(api_key__icontains=q) |
            models.Q(classroom__name__icontains=q) |
            models.Q(classroom__section__icontains=q)
        )

    @staticmethod
    def deactivate_device(device: RFIDDevice) -> None:
        """
        Deactivates a device by setting is_active=False.
        """
        device.is_active = False
        device.save(update_fields=["is_active"])

    @staticmethod
    def activate_device(device: RFIDDevice) -> None:
        """
        Activates a device by setting is_active=True.
        """
        device.is_active = True
        device.save(update_fields=["is_active"])

    @staticmethod
    def get_device_stats(user) -> dict:
        """
        Gathers device statistics for the dashboard/list headers.
        Only accessible by admins (is_staff). Returns zeros for others.
        Returns:
            total_devices: Total count of devices
            active_devices: Devices where is_active=True and last_seen is within 15 mins
            offline_devices: Devices where is_active=True and last_seen is None or > 15 mins ago
            disabled_devices: Devices where is_active=False
        """
        if not user.is_authenticated or not user.is_staff:
            return {
                "total_devices": 0,
                "active_devices": 0,
                "offline_devices": 0,
                "disabled_devices": 0,
            }

        # Calculate timezone-aware threshold for active devices (15 minutes ago)
        threshold = timezone.now() - datetime.timedelta(minutes=15)

        devices = RFIDDevice.objects.all()
        
        total_devices = devices.count()
        disabled_devices = devices.filter(is_active=False).count()
        
        # Active: is_active=True AND last_seen >= threshold
        active_devices = devices.filter(
            is_active=True, 
            last_seen__gte=threshold
        ).count()
        
        # Offline: is_active=True AND (last_seen is null OR last_seen < threshold)
        offline_devices = devices.filter(is_active=True).filter(
            models.Q(last_seen__isnull=True) | models.Q(last_seen__lt=threshold)
        ).count()

        return {
            "total_devices": total_devices,
            "active_devices": active_devices,
            "offline_devices": offline_devices,
            "disabled_devices": disabled_devices,
        }

    @staticmethod
    def get_device_status_info(device) -> dict:
        """
        Dynamically computes the device status and matching Tailwind badge CSS classes
        without database model modifications.
        """
        if not device.is_active:
            return {
                "status": "Disabled",
                "badge": "badge-danger",
            }
        
        # Calculate threshold for offline status (15 minutes ago)
        threshold = timezone.now() - datetime.timedelta(minutes=15)
        
        if device.last_seen and device.last_seen >= threshold:
            return {
                "status": "Active",
                "badge": "badge-success",
            }
        else:
            return {
                "status": "Offline",
                "badge": "badge-warning",
            }

