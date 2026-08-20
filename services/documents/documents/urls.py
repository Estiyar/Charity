from django.urls import path

from .comment_views import DocumentCommentEditView
from .file_views import DocumentOriginalView, DocumentPublicFileView
from .views import (
    CardDocumentListCreateView,
    CardPublicDocumentListView,
    DocumentRejectView,
    DocumentRequestRevisionView,
    DocumentVerifyView,
    DocumentVersionListView,
    InternalDocumentDuplicatesView,
    InternalDocumentsView,
    InternalStatsView,
    ModerationDocumentListView,
)

urlpatterns = [
    path("api/cards/<int:pk>/documents/", CardDocumentListCreateView.as_view()),
    path("api/cards/<int:pk>/documents/public/", CardPublicDocumentListView.as_view()),
    path("api/documents/<int:pk>/versions/", DocumentVersionListView.as_view()),
    path("api/documents/<int:pk>/original/", DocumentOriginalView.as_view()),
    path("api/documents/<int:pk>/public-file/", DocumentPublicFileView.as_view()),
    path("api/documents/<int:pk>/verify/", DocumentVerifyView.as_view()),
    path("api/documents/<int:pk>/reject/", DocumentRejectView.as_view()),
    path("api/documents/<int:pk>/request-revision/", DocumentRequestRevisionView.as_view()),
    path("api/documents/<int:pk>/comments/<int:comment_id>/", DocumentCommentEditView.as_view()),
    path("api/moderation/documents/", ModerationDocumentListView.as_view()),
    path("internal/cards/<int:pk>/documents/", InternalDocumentsView.as_view()),
    path("internal/documents/duplicates/", InternalDocumentDuplicatesView.as_view()),
    path("internal/stats/", InternalStatsView.as_view()),
]
