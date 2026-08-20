from django.apps import AppConfig
from django.conf import settings


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"

    def ready(self):
        from .events import EVENT_HANDLERS

        settings.EVENT_HANDLERS = EVENT_HANDLERS
