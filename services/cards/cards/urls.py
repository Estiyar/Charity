from django.urls import path

from .catalog_views import CatalogListView, CatalogReferencesView
from .comment_views import CardCommentEditView, CardCommentListView, InternalCardCommentListView
from .history_views import CardHistoryView, CardTrustStatusView
from .report_views import (
    CardReportCreateView,
    CardSuspendView,
    CardUnsuspendView,
    InternalReportRiskView,
    InternalSuspendView,
    InternalUnsuspendView,
)
from .risk_views import (
    CardRiskAssessmentView,
    CardRiskOverrideView,
    CardRiskRecalculateView,
    InternalCardRiskView,
)
from .views import (
    AdminCardListView,
    AdminCardSetStatusView,
    CardDetailView,
    CardListCreateView,
    CardSubmitView,
    InternalCardListView,
    InternalCardView,
    InternalCollectView,
    InternalEscrowView,
    InternalPhotoView,
    InternalTransitionView,
    MyCardsListView,
    RecipientVerifyView,
)

urlpatterns = [
    path("api/catalog", CatalogListView.as_view()),
    path("api/catalog/", CatalogListView.as_view()),
    path("api/catalog/references", CatalogReferencesView.as_view()),
    path("api/catalog/references/", CatalogReferencesView.as_view()),
    path("api/cards/", CardListCreateView.as_view()),
    path("api/cards/my/", MyCardsListView.as_view()),
    path("api/cards/recipient/verify", RecipientVerifyView.as_view()),
    path("api/cards/<int:pk>/", CardDetailView.as_view()),
    path("api/cards/<int:pk>/reports/", CardReportCreateView.as_view()),
    path("api/cards/<int:pk>/suspend/", CardSuspendView.as_view()),
    path("api/cards/<int:pk>/unsuspend/", CardUnsuspendView.as_view()),
    path("api/cards/<int:pk>/submit/", CardSubmitView.as_view()),
    path("api/cards/<int:pk>/comments/", CardCommentListView.as_view()),
    path("api/cards/<int:pk>/comments/<int:comment_id>/", CardCommentEditView.as_view()),
    path("api/cards/<int:pk>/trust-status/", CardTrustStatusView.as_view()),
    path("api/cards/<int:pk>/history/", CardHistoryView.as_view()),
    path("api/cards/<int:pk>/risk/", CardRiskAssessmentView.as_view()),
    path("api/cards/<int:pk>/risk/recalculate/", CardRiskRecalculateView.as_view()),
    path("api/cards/<int:pk>/risk/override/", CardRiskOverrideView.as_view()),
    path("api/admin/cards/", AdminCardListView.as_view()),
    path("api/admin/cards/<int:pk>/set-status/", AdminCardSetStatusView.as_view()),
    path("internal/cards/", InternalCardListView.as_view()),
    path("internal/cards/<int:pk>/", InternalCardView.as_view()),
    path("internal/cards/<int:pk>/suspend/", InternalSuspendView.as_view()),
    path("internal/cards/<int:pk>/unsuspend/", InternalUnsuspendView.as_view()),
    path("internal/cards/<int:pk>/report-risk/", InternalReportRiskView.as_view()),
    path("internal/cards/<int:pk>/risk/", InternalCardRiskView.as_view()),
    path("internal/cards/<int:pk>/transition/", InternalTransitionView.as_view()),
    path("internal/cards/<int:pk>/comments/", InternalCardCommentListView.as_view()),
    path("internal/cards/<int:pk>/collect/", InternalCollectView.as_view()),
    path("internal/cards/<int:pk>/escrow/", InternalEscrowView.as_view()),
    path("internal/cards/<int:pk>/photo/", InternalPhotoView.as_view()),
]
