from django.urls import path

from .views import (
    ExpenseApproveView,
    ExpenseRejectView,
    ExpenseRequestClarificationView,
)

urlpatterns = [
    path("<int:pk>/approve/", ExpenseApproveView.as_view(), name="expense-approve"),
    path("<int:pk>/reject/", ExpenseRejectView.as_view(), name="expense-reject"),
    path(
        "<int:pk>/request-clarification/",
        ExpenseRequestClarificationView.as_view(),
        name="expense-request-clarification",
    ),
]
