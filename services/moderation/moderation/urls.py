from django.urls import path

from .comment_views import ModerationCommentEditView, ModerationCommentListView
from .review_views import (
    ManualReviewApproveView,
    ManualReviewDetailView,
    ManualReviewListView,
    ManualReviewRejectView,
    ManualReviewRequestRevisionView,
    ManualReviewSuspendView,
    ManualReviewUnsuspendView,
)
from .report_views import (
    InternalReportCreateView,
    ModerationReportDetailView,
    ModerationReportListView,
    ModerationReportResolveView,
)
from .views import (
    AdminModerationLogListView,
    ModerationApproveView,
    ModerationCardDetailView,
    ModerationCardListView,
    ModerationRejectView,
    ModerationRequestRevisionView,
)

urlpatterns = [
    path("api/moderation/comments/", ModerationCommentListView.as_view()),
    path("api/moderation/comments/<int:pk>/", ModerationCommentEditView.as_view()),
    path("api/moderation/reviews/", ManualReviewListView.as_view()),
    path("api/moderation/reviews/<int:pk>/", ManualReviewDetailView.as_view()),
    path("api/moderation/reviews/<int:pk>/approve/", ManualReviewApproveView.as_view()),
    path("api/moderation/reviews/<int:pk>/reject/", ManualReviewRejectView.as_view()),
    path("api/moderation/reviews/<int:pk>/request-revision/", ManualReviewRequestRevisionView.as_view()),
    path("api/moderation/reviews/<int:pk>/suspend/", ManualReviewSuspendView.as_view()),
    path("api/moderation/reviews/<int:pk>/unsuspend/", ManualReviewUnsuspendView.as_view()),
    path("api/moderation/reports/", ModerationReportListView.as_view()),
    path("api/moderation/reports/<int:pk>/", ModerationReportDetailView.as_view()),
    path("api/moderation/reports/<int:pk>/resolve/", ModerationReportResolveView.as_view()),
    path("internal/reports/", InternalReportCreateView.as_view()),
    path("api/moderation/cards/", ModerationCardListView.as_view()),
    path("api/moderation/cards/<int:pk>/", ModerationCardDetailView.as_view()),
    path("api/moderation/cards/<int:pk>/approve/", ModerationApproveView.as_view()),
    path("api/moderation/cards/<int:pk>/reject/", ModerationRejectView.as_view()),
    path("api/moderation/cards/<int:pk>/request-revision/", ModerationRequestRevisionView.as_view()),
    path("api/admin/moderation-logs/", AdminModerationLogListView.as_view()),
]
