from django.db import models
from django.utils.text import slugify

from apps.common.models import BaseModel
from apps.courses.models import Course


class Teacher(BaseModel):
    username = models.CharField(max_length=255)
    job = models.CharField(max_length=255)
    about = models.TextField()
    direction = models.CharField(max_length=255, blank=True, null=True)
    experience = models.CharField(max_length=255, blank=True, null=True)
    work_place = models.CharField(max_length=255, blank=True, null=True)
    img = models.FileField(upload_to="teachers/")
    slug = models.SlugField(unique=True, max_length=200, blank=True, null=True)
    courses = models.ManyToManyField(Course, related_name="teachers", blank=True)

    class Meta:
        indexes = [models.Index(fields=["slug"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.username)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
