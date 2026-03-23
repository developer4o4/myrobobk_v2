import logging

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.judgenew.evaluator import evaluate
from apps.courses.models import Problem, Submission, Topic
from apps.courses.permissions import HasActiveCourseSubscription
from apps.courses.serializers import SubmitCodeSerializer

logger = logging.getLogger(__name__)

# Submission uchun alohida throttle: 1 user 30/soat
from rest_framework.throttling import UserRateThrottle


class SubmitThrottle(UserRateThrottle):
    rate = "30/hour"


class TopicSubmitView(APIView):
    """
    POST /courses/topics/<uuid:topic_id>/submit/
    Body: {language: "py|c|cpp", source_code: "..."}
    """
    permission_classes = [permissions.IsAuthenticated, HasActiveCourseSubscription]
    throttle_classes = [SubmitThrottle]

    def post(self, request, topic_id):
        topic = get_object_or_404(
            Topic.objects.select_related("section__course"), id=topic_id
        )

        self.check_object_permissions(request, topic)

        if topic.topic_type != "code":
            return Response(
                {"detail": "Bu mavzu code tipida emas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        problem = Problem.objects.filter(topic=topic).first()
        if not problem:
            return Response(
                {"detail": "Problem topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        s = SubmitCodeSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        language = s.validated_data["language"]
        source_code = s.validated_data["source_code"]

        # Submission yaratamiz (pending holda)
        sub = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=language,
            source_code=source_code,
            status="pending",
        )

        try:
            result_status, err = evaluate(problem, language, source_code)
        except Exception as e:
            logger.exception("Judge error for submission %s", sub.pk)
            sub.status = "error"
            sub.error_message = "Judge tizimida xato yuz berdi."
            sub.save(update_fields=["status", "error_message"])
            return Response(
                {"submission_id": str(sub.id), "status": "error", "error_message": sub.error_message},
                status=status.HTTP_200_OK,
            )

        sub.status = result_status
        sub.error_message = err
        sub.save(update_fields=["status", "error_message"])

        logger.info(
            "Submission: user=%s problem=%s lang=%s status=%s",
            request.user.pk, problem.pk, language, result_status,
        )

        return Response({
            "submission_id": str(sub.id),
            "status": result_status,
            "error_message": err,
        })
