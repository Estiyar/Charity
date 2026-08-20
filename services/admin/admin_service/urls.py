from django.urls import path

from .views import (
    AdminCityDeleteView,
    AdminCityListCreateView,
    AdminDiagnosisDeleteView,
    AdminDiagnosisListCreateView,
    AdminRiskConfigHistoryView,
    AdminRiskConfigView,
    AdminSettingsView,
    InternalRiskConfigView,
    InternalSettingsView,
)

urlpatterns = [
    path("api/admin/cities/", AdminCityListCreateView.as_view()),
    path("api/admin/cities/<int:pk>/", AdminCityDeleteView.as_view()),
    path("api/admin/diagnoses/", AdminDiagnosisListCreateView.as_view()),
    path("api/admin/diagnoses/<int:pk>/", AdminDiagnosisDeleteView.as_view()),
    path("api/admin/settings/", AdminSettingsView.as_view()),
    path("api/admin/risk-config/", AdminRiskConfigView.as_view()),
    path("api/admin/risk-config/history/", AdminRiskConfigHistoryView.as_view()),
    path("internal/settings/", InternalSettingsView.as_view()),
    path("internal/risk-config/", InternalRiskConfigView.as_view()),
]
