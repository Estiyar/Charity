from django.urls import path

from .views import (
    AdminDonationListView,
    ClosedRefundApiView,
    DonateView,
    DonationListView,
    MyDonationsListView,
    MyRedistributionHistoryListView,
    MyRedistributionListView,
    PlatformStatsView,
    RedistributionChooseView,
)
from .payment_views import (
    DevPaymentCompleteView,
    PaymentCallbackView,
    PaymentDetailView,
    PaymentSessionView,
    PaymentWebhookView,
)

urlpatterns = [
    path("api/payments/session", PaymentSessionView.as_view()),
    path("api/payments/callback", PaymentCallbackView.as_view()),
    path("api/payments/webhook/<str:provider>", PaymentWebhookView.as_view()),
    path("api/payments/dev/<int:pk>/complete", DevPaymentCompleteView.as_view()),
    path("api/payments/<int:pk>", PaymentDetailView.as_view()),
    path("api/cards/<int:pk>/donate/", DonateView.as_view()),
    path("api/cards/<int:pk>/donations/", DonationListView.as_view()),
    path("api/donations/my/", MyDonationsListView.as_view()),
    path("api/redistribution/my/", MyRedistributionListView.as_view()),
    path("api/redistribution/history/", MyRedistributionHistoryListView.as_view()),
    path("api/redistribution/<int:pk>/choose/", RedistributionChooseView.as_view()),
    path("api/refunds/my/", ClosedRefundApiView.as_view()),
    path("api/refunds/history/", ClosedRefundApiView.as_view()),
    path("api/refunds/<int:pk>/choose/", ClosedRefundApiView.as_view()),
    path("api/stats/", PlatformStatsView.as_view()),
    path("api/admin/donations/", AdminDonationListView.as_view()),
]
