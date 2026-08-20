from django.urls import path

from .beneficiary_views import (
    BeneficiaryDetailView,
    BeneficiaryListView,
    InternalBeneficiaryDetailView,
    InternalBeneficiaryUpsertView,
)
from .representation_views import (
    InternalRepresentationConfirmView,
    InternalRepresentationDetailView,
    RepresentationListView,
    RepresentationVerifyView,
    StaffRepresentationConfirmView,
    StaffRepresentationListView,
    StaffRepresentationRejectView,
)
from .views import MeProfileView, ProfileDetailView

urlpatterns = [
    path("api/profile/me", MeProfileView.as_view()),
    path("api/profile/<int:user_id>", ProfileDetailView.as_view()),
    path("api/beneficiaries", BeneficiaryListView.as_view()),
    path("api/beneficiaries/<int:pk>", BeneficiaryDetailView.as_view()),
    path("api/representations", RepresentationListView.as_view()),
    path("api/representations/verify", RepresentationVerifyView.as_view()),
    path("api/representations/moderation", StaffRepresentationListView.as_view()),
    path("api/representations/<int:pk>/confirm", StaffRepresentationConfirmView.as_view()),
    path("api/representations/<int:pk>/reject", StaffRepresentationRejectView.as_view()),
    path("internal/beneficiaries/", InternalBeneficiaryUpsertView.as_view()),
    path("internal/beneficiaries/<int:pk>/", InternalBeneficiaryDetailView.as_view()),
    path("internal/representations/<int:pk>/", InternalRepresentationDetailView.as_view()),
    path("internal/representations/<int:pk>/confirm/", InternalRepresentationConfirmView.as_view()),
]
