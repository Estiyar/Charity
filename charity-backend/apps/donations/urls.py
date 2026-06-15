from django.urls import path

from .views import MyDonationsListView, PlatformStatsView

urlpatterns = [
    path("stats/", PlatformStatsView.as_view(), name="platform-stats"),
    path("donations/my/", MyDonationsListView.as_view(), name="my-donations"),
]
