from rest_framework import serializers

from apps.courses.models import (
    Course, Problem, Section, Topic, CourseType,
    TopicView, SectionCompletion
)


class ProblemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = ("title", "statement", "sample_input", "sample_output")

class CourseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseType
        fields = ['id', 'title']

class CourseSerializer(serializers.ModelSerializer):
    buyers_total = serializers.IntegerField(read_only=True)
    buyers_active = serializers.IntegerField(read_only=True)
    sections_count = serializers.IntegerField(read_only=True)
    topics_count = serializers.IntegerField(read_only=True)
    is_bought = serializers.BooleanField(read_only=True)

    class Meta:
        model = Course
        fields = (
            "id", "title", "about", "image", "price", "is_active",
            "buyers_total", "buyers_active",
            "sections_count", "topics_count",
            "is_bought",
        )


class TopicSerializer(serializers.ModelSerializer):
    is_code = serializers.BooleanField(read_only=True)
    problems = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ("id", "title", "about", "video_url", "vdo_video_id", "topic_type", "is_code", "order", "problems")

    def get_problems(self, obj):
        if obj.topic_type == "code":
            return ProblemSerializer(obj.problem.all(), many=True).data
        return []


class TopicMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ("id", "title", "topic_type", "order", "is_code")


class SectionSerializer(serializers.ModelSerializer):
    topics = TopicMiniSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ("id", "title", "order", "topics")


class BuyCourseSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()


class MyCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ("id", "title", "about", "image", "price")


class SubmitCodeSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=["py", "c", "cpp"])
    source_code = serializers.CharField(max_length=65536)  # 64KB limit


class TopicViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicView
        fields = ("id", "topic", "viewed_at")
        read_only_fields = ("id", "viewed_at")


class SectionCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionCompletion
        fields = ("id", "section", "completed_at")
        read_only_fields = ("id", "completed_at")

