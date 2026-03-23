from django.contrib import admin

from .models import Blog, Category, Comment, WaitBlog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_active")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "views", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("views", "created_at", "updated_at")
    list_editable = ("status",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "blog", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("user__phone", "blog__title")


@admin.register(WaitBlog)
class WaitBlogAdmin(admin.ModelAdmin):
    list_display = ("blog", "created_at")
    raw_id_fields = ("blog",)
