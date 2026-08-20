from django.urls import path

from .internal_views import InternalUserListView, InternalUserSetStatusView
from .views import (
    AdminModeratorListView,
    AdminUserDetailView,
    AdminUserListView,
    BalanceView,
    BalanceWithdrawView,
    EcpChallengeView,
    EcpRegisterView,
    EcpVerifyView,
    InternalConsumeChallengeView,
    InternalCreditView,
    InternalUserView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path("api/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/auth/register/ecp", EcpRegisterView.as_view(), name="auth-register-ecp"),
    path("api/auth/ecp/challenge", EcpChallengeView.as_view(), name="auth-ecp-challenge"),
    path("api/auth/ecp/verify", EcpVerifyView.as_view(), name="auth-ecp-verify"),
    path("api/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/me", MeView.as_view(), name="auth-me"),
    path("api/auth/balance/", BalanceView.as_view(), name="auth-balance"),
    path("api/auth/balance/withdraw/", BalanceWithdrawView.as_view(), name="auth-balance-withdraw"),
    path("api/admin/users/", AdminUserListView.as_view(), name="admin-users"),
    path("api/admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("api/admin/moderators/", AdminModeratorListView.as_view(), name="admin-moderators"),
    path("internal/users/", InternalUserListView.as_view(), name="internal-users"),
    path("internal/users/<int:pk>/", InternalUserView.as_view(), name="internal-user"),
    path("internal/users/<int:pk>/set-status/", InternalUserSetStatusView.as_view(), name="internal-user-status"),
    path("internal/users/<int:pk>/credit/", InternalCreditView.as_view(), name="internal-credit"),
    path("internal/ecp/challenges/consume/", InternalConsumeChallengeView.as_view(), name="internal-ecp-consume"),
]
