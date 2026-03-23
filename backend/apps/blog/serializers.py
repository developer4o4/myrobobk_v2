from rest_framework import serializers

from .models import Blog, Category, Comment


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "title", "slug"]


class BlogListSerializer(serializers.ModelSerializer):
    category = CategoryListSerializer(read_only=True)

    class Meta:
        model = Blog
        fields = ["id", "title", "slug", "img", "views", "category", "created_at"]


class BlogDetailSerializer(serializers.ModelSerializer):
    category = CategoryListSerializer(read_only=True)

    class Meta:
        model = Blog
        fields = [
            "id", "title", "slug", "description",
            "img", "views", "category", "created_at", "updated_at",
        ]


class CommentListSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "user", "text", "created_at"]


class CommentCreateSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=2, max_length=2000)

    def validate_text(self, value):
        return value.strip()


class BlogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ["id", "category", "title", "description", "img"]
