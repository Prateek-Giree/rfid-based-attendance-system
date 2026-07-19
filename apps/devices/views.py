from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View
from apps.core.mixins import AdminRequiredMixin
from .models import RFIDDevice
from .forms import DeviceForm
from apps.attendance.services.device_service import DeviceService


class DeviceListView(AdminRequiredMixin, ListView):
    """
    Renders paginated list of all RFID devices.
    - Admin only.
    - Supports live searching via HTMX.
    """
    model = RFIDDevice
    paginate_by = 10
    context_object_name = "devices"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["devices/partials/device_table.html"]
        return ["devices/device_list.html"]

    def get_queryset(self):
        queryset = RFIDDevice.objects.select_related("classroom").all()
        q = self.request.GET.get("q", "").strip()
        queryset = DeviceService.search_devices(queryset, q)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch status stats dynamically using DeviceService
        stats = DeviceService.get_device_stats(self.request.user)
        context.update(stats)

        # Attach computed status and badge classes to the list object list
        page_obj = context.get("page_obj")
        if page_obj:
            for device in page_obj.object_list:
                status_info = DeviceService.get_device_status_info(device)
                device.derived_status = status_info["status"]
                device.status_badge_class = status_info["badge"]

        context["page_title"] = "Devices"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Devices", "url": None},
        ]
        context["q"] = self.request.GET.get("q", "").strip()
        return context


class DeviceDetailView(AdminRequiredMixin, DetailView):
    """
    Renders detailed view of an RFID device.
    - Admin only.
    """
    model = RFIDDevice
    context_object_name = "device"
    template_name = "devices/device_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device = self.object
        
        # Attach computed status details
        status_info = DeviceService.get_device_status_info(device)
        device.derived_status = status_info["status"]
        device.status_badge_class = status_info["badge"]

        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Devices", "url": reverse_lazy("devices:device_list")},
            {"label": device.name, "url": None},
        ]
        return context


class DeviceCreateView(AdminRequiredMixin, CreateView):
    """
    Handles registering a new RFID device.
    - Admin only.
    """
    model = RFIDDevice
    form_class = DeviceForm
    template_name = "devices/device_form.html"
    success_url = reverse_lazy("devices:device_list")

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Device '{self.object.name}' registered successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Register Device"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Devices", "url": reverse_lazy("devices:device_list")},
            {"label": "Register", "url": None},
        ]
        return context


class DeviceUpdateView(AdminRequiredMixin, UpdateView):
    """
    Handles editing device details (name, classroom assignment, is_active).
    - Admin only.
    """
    model = RFIDDevice
    form_class = DeviceForm
    template_name = "devices/device_form.html"
    success_url = reverse_lazy("devices:device_list")

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Device '{self.object.name}' updated successfully.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Edit Device"
        context["breadcrumbs"] = [
            {"label": "Dashboard", "url": reverse_lazy("auth_core:dashboard")},
            {"label": "Devices", "url": reverse_lazy("devices:device_list")},
            {"label": self.object.name, "url": reverse_lazy("devices:device_detail", kwargs={"pk": self.object.pk})},
            {"label": "Edit", "url": None},
        ]
        return context


class DeviceDeactivateView(AdminRequiredMixin, View):
    """
    Soft-deactivates (disables) a device by setting is_active=False.
    - Admin only.
    - Triggered via SweetAlert2 confirmation.
    """

    def post(self, request, *args, **kwargs):
        device = get_object_or_404(RFIDDevice, pk=self.kwargs["pk"])
        try:
            DeviceService.deactivate_device(device)
            messages.success(request, f"Device '{device.name}' has been disabled.")
        except Exception as e:
            messages.error(request, str(e))
        return HttpResponseRedirect(reverse_lazy("devices:device_list"))
