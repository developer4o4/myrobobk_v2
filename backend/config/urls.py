from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("user/", include("apps.users.urls")),
    path("courses/", include("apps.courses.urls")),
    path("blog/", include("apps.blog.urls")),
    path("teacher/", include("apps.teachers.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
