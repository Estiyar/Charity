from django.urls import path

from .ecp_views import InternalEcpVerificationView, InternalEcpVerifyView
from .recipient_views import InternalRecipientVerifyView
from .views import (
    FraudProfileLookupView,
    InternalFraudProfileByHashView,
    InternalFraudProfileLookupView,
    InternalMedicalRecordByHashView,
    InternalMedicalRecordLookupView,
    MedicalRecordLookupView,
)

urlpatterns = [
    path("api/medregistry/lookup/", MedicalRecordLookupView.as_view()),
    path("api/antifraud/lookup/", FraudProfileLookupView.as_view()),
    path("internal/medregistry/lookup/", InternalMedicalRecordLookupView.as_view()),
    path("internal/antifraud/lookup/", InternalFraudProfileLookupView.as_view()),
    path("internal/medregistry/hash/<str:iin_hash>/", InternalMedicalRecordByHashView.as_view()),
    path("internal/antifraud/hash/<str:iin_hash>/", InternalFraudProfileByHashView.as_view()),
    path("internal/ecp/verify/", InternalEcpVerifyView.as_view()),
    path("internal/ecp/verifications/<int:pk>/", InternalEcpVerificationView.as_view()),
    path("internal/recipient/verify/", InternalRecipientVerifyView.as_view()),
]
