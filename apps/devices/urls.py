from django.urls import path
from . import views

app_name = "devices"

urlpatterns = [
    path("devices/", views.DeviceListView.as_view(), name="device_list"),
    path("devices/create/", views.DeviceCreateView.as_view(), name="device_create"),
    path("devices/<int:pk>/", views.DeviceDetailView.as_view(), name="device_detail"),
    path("devices/<int:pk>/edit/", views.DeviceUpdateView.as_view(), name="device_update"),
    path("devices/<int:pk>/deactivate/", views.DeviceDeactivateView.as_view(), name="device_deactivate"),
]
