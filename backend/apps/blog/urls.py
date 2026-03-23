from django.urls import path

from .views import (
    BlogCommentsAPIView,
    BlogCreateAPIView,
    BlogDetailAPIView,
    BlogListAPIView,
    CategoryListAPIView,
)

urlpatterns = [
    path("categories/", CategoryListAPIView.as_view(), name="category-list"),
    path("blogs/", BlogListAPIView.as_view(), name="blog-list"),
    path("blog-create/", BlogCreateAPIView.as_view(), name="blog-create"),
    path("blogs/<slug:slug>/", BlogDetailAPIView.as_view(), name="blog-detail"),
    path("blogs/<slug:slug>/comments/", BlogCommentsAPIView.as_view(), name="blog-comments"),
]
