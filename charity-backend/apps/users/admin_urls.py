from django.urls import path

from .admin_views import (
    AdminCardListView,
    AdminCardSetStatusView,
    AdminCardStatusView,
    AdminCityDeleteView,
    AdminCityListCreateView,
    AdminDiagnosisDeleteView,
    AdminDiagnosisListCreateView,
    AdminDonationListView,
    AdminExpenseListView,
    AdminModerationLogListView,
    AdminModeratorListView,
    AdminSettingsView,
    AdminUserDetailView,
    AdminUserListView,
)

urlpatterns = [
    path("users/", AdminUserListView.as_view(), name="admin-users"),
    path("users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("moderators/", AdminModeratorListView.as_view(), name="admin-moderators"),
    path("cards/", AdminCardListView.as_view(), name="admin-cards"),
    path("cards/<int:pk>/", AdminCardStatusView.as_view(), name="admin-card-status"),
    path(
        "cards/<int:pk>/set-status/",
        AdminCardSetStatusView.as_view(),
        name="admin-card-set-status",
    ),
    path("donations/", AdminDonationListView.as_view(), name="admin-donations"),
    path("expenses/", AdminExpenseListView.as_view(), name="admin-expenses"),
    path("moderation-logs/", AdminModerationLogListView.as_view(), name="admin-logs"),
    path("cities/", AdminCityListCreateView.as_view(), name="admin-cities"),
    path("cities/<int:pk>/", AdminCityDeleteView.as_view(), name="admin-city-delete"),
    path("diagnoses/", AdminDiagnosisListCreateView.as_view(), name="admin-diagnoses"),
    path(
        "diagnoses/<int:pk>/",
        AdminDiagnosisDeleteView.as_view(),
        name="admin-diagnosis-delete",
    ),
    path("settings/", AdminSettingsView.as_view(), name="admin-settings"),
]
