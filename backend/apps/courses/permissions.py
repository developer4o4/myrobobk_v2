from django.utils import timezone
from rest_framework.permissions import BasePermission

from apps.courses.models import CourseSubscription, Topic


class HasActiveCourseSubscription(BasePermission):
    message = "Kurs yopiq. To'lov qiling."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if isinstance(obj, Topic):
            course = obj.section.course
        elif hasattr(obj, "course"):
            course = obj.course
        else:
            course = obj

        return CourseSubscription.objects.filter(
            user=user,
            course=course,
            active=True,
            expires_at__gt=timezone.now(),
        ).exists()
