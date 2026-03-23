import logging

from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Blog, Category, Comment, WaitBlog
from .serializers import (
    BlogCreateSerializer,
    BlogDetailSerializer,
    BlogListSerializer,
    CategoryListSerializer,
    CommentCreateSerializer,
    CommentListSerializer,
)

logger = logging.getLogger(__name__)


class CategoryListAPIView(ListAPIView):
    queryset = Category.objects.filter(is_active=True).order_by("title", "id")
    serializer_class = CategoryListSerializer
    permission_classes = [permissions.AllowAny]


class BlogListAPIView(APIView):
    """
    GET /blog/blogs/?category=<slug|id>
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = (
            Blog.objects
            .select_related("category")
            .filter(status=True, is_active=True)
            .order_by("-created_at", "-id")
        )

        category_param = request.query_params.get("category")
        if category_param:
            if category_param.isdigit():
                qs = qs.filter(category_id=int(category_param))
            else:
                qs = qs.filter(category__slug=category_param)

        serializer = BlogListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class BlogDetailAPIView(APIView):
    """GET /blog/blogs/<slug>/"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        blog = get_object_or_404(
            Blog.objects.select_related("category").filter(status=True),
            slug=slug,
        )
        # views ni atomic increment
        Blog.objects.filter(id=blog.id).update(views=F("views") + 1)
        blog.refresh_from_db(fields=["views"])

        return Response(BlogDetailSerializer(blog, context={"request": request}).data)


class BlogCommentsAPIView(APIView):
    """
    GET  /blog/blogs/<slug>/comments/
    POST /blog/blogs/<slug>/comments/  (login kerak)
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, slug):
        blog = get_object_or_404(Blog, slug=slug, status=True)
        qs = (
            Comment.objects
            .select_related("user")
            .filter(blog=blog, is_active=True)
            .order_by("-created_at")
        )
        return Response({
            "blog": {"id": blog.id, "title": blog.title, "slug": blog.slug},
            "count": qs.count(),
            "results": CommentListSerializer(qs, many=True).data,
        })

    def post(self, request, slug):
        blog = get_object_or_404(Blog, slug=slug, status=True)

        s = CommentCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        comment = Comment.objects.create(
            blog=blog,
            user=request.user,
            text=s.validated_data["text"],
        )
        return Response(CommentListSerializer(comment).data, status=status.HTTP_201_CREATED)


class BlogCreateAPIView(CreateAPIView):
    queryset = Blog.objects.all()
    serializer_class = BlogCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        blog = serializer.save(status=False)
        WaitBlog.objects.create(blog=blog)
        logger.info("New blog submitted by user=%s title=%r", self.request.user.pk, blog.title)
