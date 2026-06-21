from django.urls import path

from apps.documents.views import CardDocumentListCreateView
from apps.donations.views import DonateView, DonationListView
from apps.expenses.views import CardExpenseListCreateView

from .views import CardDetailView, CardListCreateView, CardSubmitView, MyCardsListView

urlpatterns = [
    path("", CardListCreateView.as_view(), name="card-list-create"),
    path("my/", MyCardsListView.as_view(), name="card-my-list"),
    path("<int:pk>/", CardDetailView.as_view(), name="card-detail"),
    path("<int:pk>/submit/", CardSubmitView.as_view(), name="card-submit"),
    path(
        "<int:pk>/documents/",
        CardDocumentListCreateView.as_view(),
        name="card-documents",
    ),
    path("<int:pk>/donate/", DonateView.as_view(), name="card-donate"),
    path("<int:pk>/donations/", DonationListView.as_view(), name="card-donations"),
    path("<int:pk>/expenses/", CardExpenseListCreateView.as_view(), name="card-expenses"),
]
