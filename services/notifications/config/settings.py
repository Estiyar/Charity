from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from ekomek_common.django_settings import build_settings

globals().update(
    build_settings(
        service_name="notifications",
        schema="notifications",
        base_dir=Path(__file__).resolve().parent.parent,
        extra_apps=["notifications"],
        auth_user_model=None,
        use_identity_jwt=False,
    )
)

NOTIFICATION_EMAIL_ADAPTER = "dev"
NOTIFICATION_SMS_ADAPTER = "dev"
NOTIFICATION_PUSH_ADAPTER = "dev"
NOTIFICATION_DELIVERY_MAX_ATTEMPTS = 3
NOTIFICATION_DEADLINE_WARNING_DAYS = 3

CELERY_BEAT_SCHEDULE["process-notification-deliveries"] = {
    "task": "notifications.tasks.process_notification_deliveries",
    "schedule": 30.0,
}
CELERY_BEAT_SCHEDULE["notify-upcoming-deadlines"] = {
    "task": "notifications.tasks.notify_upcoming_deadlines",
    "schedule": 3600.0,
}
