from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("classrooms/", views.ClassroomListView.as_view(), name="classroom_list"),
    path("classrooms/create/", views.ClassroomCreateView.as_view(), name="classroom_create"),
    path("classrooms/<int:pk>/", views.ClassroomDetailView.as_view(), name="classroom_detail"),
    path("classrooms/<int:pk>/edit/", views.ClassroomUpdateView.as_view(), name="classroom_update"),
    path("classrooms/<int:pk>/delete/", views.ClassroomDeleteView.as_view(), name="classroom_delete"),
]
