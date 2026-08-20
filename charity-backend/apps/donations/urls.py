from django.urls import path

from .views import (
    ClosedRefundApiView,
    MyDonationsListView,
    MyRedistributionHistoryListView,
    MyRedistributionListView,
    PlatformStatsView,
    RedistributionChooseView,
)

urlpatterns = [
    path("stats/", PlatformStatsView.as_view(), name="platform-stats"),
    path("donations/my/", MyDonationsListView.as_view(), name="my-donations"),
    path("redistribution/my/", MyRedistributionListView.as_view(), name="my-redistribution"),
    path("redistribution/history/", MyRedistributionHistoryListView.as_view(), name="my-redistribution-history"),
    path("redistribution/<int:pk>/choose/", RedistributionChooseView.as_view(), name="redistribution-choose"),
    path("refunds/my/", ClosedRefundApiView.as_view(), name="my-refunds"),
    path("refunds/history/", ClosedRefundApiView.as_view(), name="my-refund-history"),
    path("refunds/<int:pk>/choose/", ClosedRefundApiView.as_view(), name="refund-choose"),
]
