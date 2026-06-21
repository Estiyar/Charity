from django.urls import path

from .views import (
    MyDonationsListView,
    MyRefundDecisionsListView,
    MyRefundHistoryListView,
    PlatformStatsView,
    RefundDecisionChooseView,
)

urlpatterns = [
    path("stats/", PlatformStatsView.as_view(), name="platform-stats"),
    path("donations/my/", MyDonationsListView.as_view(), name="my-donations"),
    path("refunds/my/", MyRefundDecisionsListView.as_view(), name="my-refunds"),
    path("refunds/history/", MyRefundHistoryListView.as_view(), name="my-refund-history"),
    path("refunds/<int:pk>/choose/", RefundDecisionChooseView.as_view(), name="refund-choose"),
]
