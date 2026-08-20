from datetime import date

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from ekomek_common.http import ServiceClientError, cards_client

from .repositories import NotificationDeliveryRepository
from .services import notify_upcoming_deadline, send_delivery


@shared_task(name="notifications.tasks.send_notification_delivery")
def send_notification_delivery(delivery_id):
    from .models import NotificationDelivery

    delivery = NotificationDelivery.objects.filter(pk=delivery_id).first()
    if delivery is None:
        return None
    try:
        send_delivery(delivery)
    except Exception:
        return None
    return delivery_id


@shared_task(name="notifications.tasks.process_notification_deliveries")
def process_notification_deliveries(batch_size=100):
    for delivery in NotificationDeliveryRepository().due()[:batch_size]:
        send_notification_delivery.delay(delivery.id)
    return batch_size


@shared_task(name="notifications.tasks.notify_upcoming_deadlines")
def notify_upcoming_deadlines_task():
    try:
        cards = cards_client().get("/internal/cards/", params={"status": "active"}) or []
    except ServiceClientError:
        return 0
    notified = 0
    today = timezone.localdate()
    warning_days = int(getattr(settings, "NOTIFICATION_DEADLINE_WARNING_DAYS", 3))
    for card in cards:
        end_date = card.get("end_date")
        if not end_date:
            continue
        try:
            card_end_date = date.fromisoformat(str(end_date)[:10])
        except ValueError:
            continue
        days_left = (card_end_date - today).days
        if days_left < 0 or days_left > warning_days:
            continue
        if notify_upcoming_deadline(card):
            notified += 1
    return notified
