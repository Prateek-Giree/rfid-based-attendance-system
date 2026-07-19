from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    # Classrooms
    path("classrooms/", views.ClassroomListView.as_view(), name="classroom_list"),
    path("classrooms/create/", views.ClassroomCreateView.as_view(), name="classroom_create"),
    path("classrooms/<int:pk>/", views.ClassroomDetailView.as_view(), name="classroom_detail"),
    path("classrooms/<int:pk>/edit/", views.ClassroomUpdateView.as_view(), name="classroom_update"),
    path("classrooms/<int:pk>/delete/", views.ClassroomDeleteView.as_view(), name="classroom_delete"),

    # Students
    path("students/", views.StudentListView.as_view(), name="student_list"),
    path("students/create/", views.StudentCreateView.as_view(), name="student_create"),
    path("students/<int:pk>/", views.StudentDetailView.as_view(), name="student_detail"),
    path("students/<int:pk>/edit/", views.StudentUpdateView.as_view(), name="student_update"),
    path("students/<int:pk>/delete/", views.StudentDeleteView.as_view(), name="student_delete"),
]
