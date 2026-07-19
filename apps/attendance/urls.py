from django.urls import path
from . import views, api_views

app_name = "attendance"

urlpatterns = [
    path("attendance/", views.AttendanceListView.as_view(), name="attendance_list"),
    path("attendance/mark/", views.AttendanceMarkView.as_view(), name="attendance_mark"),
    path("attendance/student/<int:pk>/", views.AttendanceStudentHistoryView.as_view(), name="student_history"),
    path("attendance/<int:pk>/delete/", views.AttendanceDeleteView.as_view(), name="attendance_delete"),
    path("api/rfid/scan/", api_views.RFIDScanView.as_view(), name="rfid_scan"),
    
    # Student Portal
    path("portal/", views.StudentPortalView.as_view(), name="portal"),
    path("portal/lookup/", views.StudentPortalLookupView.as_view(), name="portal_lookup"),
    
    # Reports
    path("attendance/reports/", views.AttendanceReportView.as_view(), name="report"),
    path("attendance/reports/export/", views.AttendanceReportExportView.as_view(), name="report_export"),
]
