from rest_framework import serializers

from .models import Teacher


class _CourseMinimalSerializer(serializers.Serializer):
    """Teacher ichida kurslarni minimal ko'rsatish."""
    id = serializers.UUIDField()
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)


class _CourseFullSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    about = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        request = self.context.get("request")
        if getattr(obj, "image", None) and obj.image:
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class TeacherListSerializer(serializers.ModelSerializer):
    img = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = [
            "id", "username", "job", "direction",
            "experience", "about", "work_place", "img", "slug", "courses",
        ]

    def get_img(self, obj):
        request = self.context.get("request")
        if obj.img:
            return request.build_absolute_uri(obj.img.url) if request else obj.img.url
        return None

    def get_courses(self, obj):
        return _CourseMinimalSerializer(obj.courses.all(), many=True).data


class TeacherDetailSerializer(serializers.ModelSerializer):
    img = serializers.SerializerMethodField()
    courses = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = [
            "id", "username", "job", "about", "direction",
            "experience", "work_place", "img", "slug", "courses", "created_at",
        ]

    def get_img(self, obj):
        request = self.context.get("request")
        if obj.img:
            return request.build_absolute_uri(obj.img.url) if request else obj.img.url
        return None

    def get_courses(self, obj):
        return _CourseFullSerializer(
            obj.courses.all(), many=True, context=self.context
        ).data
