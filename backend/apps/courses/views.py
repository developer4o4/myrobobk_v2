from django.db.models import BooleanField, Count, Exists, OuterRef, Q, Value
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Course, CourseSubscription, Section, Topic
from apps.courses.permissions import HasActiveCourseSubscription
from apps.courses.serializers import (
    BuyCourseSerializer,
    CourseSerializer,
    MyCourseSerializer,
    SectionSerializer,
    TopicMiniSerializer,
    TopicSerializer,
)


class CourseListView(ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        qs = (
            Course.objects
            .filter(is_active=True)
            .annotate(
                buyers_total=Count("subscriptions__user", distinct=True),
                buyers_active=Count(
                    "subscriptions__user",
                    filter=Q(subscriptions__active=True, subscriptions__expires_at__gt=now),
                    distinct=True,
                ),
                sections_count=Count("sections", distinct=True),
                topics_count=Count("sections__topics", distinct=True),
            )
            .order_by("-created_at")
        )

        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            active_sub = CourseSubscription.objects.filter(
                user=user, course=OuterRef("pk"), active=True, expires_at__gt=now,
            )
            qs = qs.annotate(is_bought=Exists(active_sub))
        else:
            qs = qs.annotate(is_bought=Value(False, output_field=BooleanField()))

        return qs


class BuyCourseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        s = BuyCourseSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        course = get_object_or_404(Course, id=s.validated_data["course_id"], is_active=True)

        try:
            sub = CourseSubscription.start_or_renew(request.user, course)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "ok": True,
            "course_id": str(course.id),
            "expires_at": sub.expires_at,
            "active": sub.active,
        })


class CourseSectionsView(ListAPIView):
    """GET /courses/courses/<course_id>/sections/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = SectionSerializer

    def get_queryset(self):
        course = get_object_or_404(Course, id=self.kwargs["course_id"], is_active=True)
        return (
            Section.objects
            .filter(course=course)
            .prefetch_related("topics")
            .order_by("order", "id")
        )


class SectionTopicsView(ListAPIView):
    """GET /courses/sections/<section_id>/topics/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = TopicMiniSerializer

    def get_queryset(self):
        section = get_object_or_404(Section, id=self.kwargs["section_id"])
        return Topic.objects.filter(section=section).order_by("order", "id")


class TopicDetailView(RetrieveAPIView):
    """GET /courses/topics/<pk>/"""
    queryset = Topic.objects.select_related("section__course")
    serializer_class = TopicSerializer
    permission_classes = [permissions.IsAuthenticated, HasActiveCourseSubscription]


class MyPurchasedCoursesView(ListAPIView):
    """GET /courses/my-courses/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MyCourseSerializer

    def get_queryset(self):
        subs = (
            CourseSubscription.objects
            .filter(user=self.request.user, active=True, expires_at__gt=timezone.now())
            .select_related("course")
            .order_by("-expires_at")
        )
        return [s.course for s in subs]
