from django.urls import path

from .views import NotificationListView, NotificationReadAllView, NotificationReadView, NotificationUnreadView

urlpatterns = [
    path("api/notifications", NotificationListView.as_view()),
    path("api/notifications/<int:pk>/read", NotificationReadView.as_view()),
    path("api/notifications/<int:pk>/unread", NotificationUnreadView.as_view()),
    path("api/notifications/read-all", NotificationReadAllView.as_view()),
]
