
from django.urls import path
from apps.courses.views import (
    CourseSectionsView,
    CourseListView,
    MyPurchasedCoursesView,
    SectionTopicsView,
    TopicDetailView,
    CourseTypeListView,
    CoursesByCourseTypeView,
)
from apps.courses.views_payme import (
    BuyCourseView,
    CardCreateView,
    CardVerifyView,
    CardListView,
    CardDeleteView,
    CardSetDefaultView,
    CancelSubscriptionView,
)
from apps.courses.views_submission import TopicSubmitView
from apps.courses.views_payme_webhook import PaymeWebhookView


urlpatterns = [
    # ── Kurslar ────────────────────────────────────────────────────
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("courses/<uuid:course_id>/sections/", CourseSectionsView.as_view(), name="course-sections"),
    path("my-courses/", MyPurchasedCoursesView.as_view(), name="my-courses"),
    path("course-types/", CourseTypeListView.as_view()),
    path("course-types/<uuid:course_type_id>/courses/", CoursesByCourseTypeView.as_view()),
 
    # ── Mavzular ───────────────────────────────────────────────────
    path("sections/<uuid:section_id>/topics/", SectionTopicsView.as_view(), name="section-topics"),
    path("topics/<uuid:pk>/", TopicDetailView.as_view(), name="topic-detail"),
    path("topics/<uuid:topic_id>/submit/", TopicSubmitView.as_view(), name="topic-submit"),
 
    # ── Payme: Kartalar ────────────────────────────────────────────
    path("payments/cards/", CardListView.as_view(), name="card-list"),
    path("payments/cards/create/", CardCreateView.as_view(), name="card-create"),
    path("payments/cards/verify/", CardVerifyView.as_view(), name="card-verify"),
    path("payments/cards/<uuid:card_id>/delete/", CardDeleteView.as_view(), name="card-delete"),
    path("payments/cards/<uuid:card_id>/set-default/", CardSetDefaultView.as_view(), name="card-set-default"),
 
    # ── Payme: Sotib olish ─────────────────────────────────────────
    path("courses/buy/", BuyCourseView.as_view(), name="course-buy"),
    path("courses/<uuid:course_id>/cancel-subscription/", CancelSubscriptionView.as_view(), name="cancel-subscription"),
    path("payments/payme/webhook/", PaymeWebhookView.as_view(), name="payme-webhook"),
]
 