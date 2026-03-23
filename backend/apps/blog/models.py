from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import BaseModel

try:
    from ckeditor.fields import RichTextField
except ImportError:
    RichTextField = models.TextField  # fallback

User = settings.AUTH_USER_MODEL


class Category(BaseModel):
    title = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Blog(BaseModel):
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="blogs"
    )
    title = models.CharField(max_length=255)
    description = RichTextField()
    status = models.BooleanField(default=False)
    img = models.FileField(upload_to="blog/")
    slug = models.CharField(max_length=255, unique=True, blank=True)
    views = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Comment(BaseModel):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()

    class Meta:
        indexes = [models.Index(fields=["blog", "-created_at"])]

    def __str__(self):
        return f"{self.user} - {self.blog.title[:30]}"


class WaitBlog(BaseModel):
    """Moderatsiya kutayotgan bloglar."""
    blog = models.OneToOneField(Blog, on_delete=models.CASCADE, related_name="wait_entry")

    def __str__(self):
        return f"Waiting: {self.blog.title[:40]}"
