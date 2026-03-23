from django.urls import path

from .views import TeacherDetailAPIView, TeachersListAPIView

urlpatterns = [
    path("teachers/", TeachersListAPIView.as_view(), name="teachers-list"),
    path("teachers/<slug:slug>/", TeacherDetailAPIView.as_view(), name="teacher-detail"),
]
