from django.urls import path

from apps.expenses.views import ModerationExpenseListView

from .views import (
    ModerationApproveView,
    ModerationCardDetailView,
    ModerationCardListView,
    ModerationDocumentListView,
    ModerationRejectView,
    ModerationRequestRevisionView,
)

urlpatterns = [
    path("cards/", ModerationCardListView.as_view(), name="moderation-card-list"),
    path("cards/<int:pk>/", ModerationCardDetailView.as_view(), name="moderation-card-detail"),
    path("cards/<int:pk>/approve/", ModerationApproveView.as_view(), name="moderation-approve"),
    path("cards/<int:pk>/reject/", ModerationRejectView.as_view(), name="moderation-reject"),
    path(
        "cards/<int:pk>/request-revision/",
        ModerationRequestRevisionView.as_view(),
        name="moderation-request-revision",
    ),
    path("documents/", ModerationDocumentListView.as_view(), name="moderation-document-list"),
    path("expenses/", ModerationExpenseListView.as_view(), name="moderation-expense-list"),
]
