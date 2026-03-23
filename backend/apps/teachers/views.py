from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Teacher
from .serializers import TeacherDetailSerializer, TeacherListSerializer


class TeachersListAPIView(ListAPIView):
    serializer_class = TeacherListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Teacher.objects
            .filter(is_active=True)
            .prefetch_related("courses")
            .order_by("-created_at")
        )


class TeacherDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        teacher = get_object_or_404(
            Teacher.objects.filter(is_active=True).prefetch_related("courses"),
            slug=slug,
        )
        return Response(
            TeacherDetailSerializer(teacher, context={"request": request}).data
        )
