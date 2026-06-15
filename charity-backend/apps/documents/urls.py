from django.urls import path

from .views import DocumentRejectView, DocumentVerifyView

urlpatterns = [
    path("<int:pk>/verify/", DocumentVerifyView.as_view(), name="document-verify"),
    path("<int:pk>/reject/", DocumentRejectView.as_view(), name="document-reject"),
]
