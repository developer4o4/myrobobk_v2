from django.urls import path

from apps.courses.views import (
    BuyCourseView,
    CourseSectionsView,
    CourseListView,
    MyPurchasedCoursesView,
    SectionTopicsView,
    TopicDetailView,
)
from apps.courses.views_submission import TopicSubmitView

urlpatterns = [
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("courses/buy/", BuyCourseView.as_view(), name="course-buy"),
    path("courses/<uuid:course_id>/sections/", CourseSectionsView.as_view(), name="course-sections"),
    path("sections/<uuid:section_id>/topics/", SectionTopicsView.as_view(), name="section-topics"),
    path("topics/<uuid:pk>/", TopicDetailView.as_view(), name="topic-detail"),
    path("topics/<uuid:topic_id>/submit/", TopicSubmitView.as_view(), name="topic-submit"),
    path("my-courses/", MyPurchasedCoursesView.as_view(), name="my-courses"),
]
