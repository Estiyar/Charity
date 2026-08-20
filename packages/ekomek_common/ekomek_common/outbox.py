import logging
import uuid

from celery import shared_task
from django.utils import timezone

from ekomek_common.constants import EVENT_SUBSCRIPTIONS, SERVICE_QUEUES

logger = logging.getLogger(__name__)


def enqueue_event(event_type, aggregate_type, aggregate_id, payload):
    from ekomek_common.outbox_app.models import OutboxEvent

    return OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload=payload,
    )


def publish_event_now(event_type, payload):
    from celery import current_app

    subscribers = EVENT_SUBSCRIPTIONS.get(event_type, [])
    for service_name in subscribers:
        queue_name = SERVICE_QUEUES[service_name]
        current_app.send_task(
            "ekomek_common.handle_domain_event",
            kwargs={"event_type": event_type, "payload": payload},
            queue=queue_name,
        )


@shared_task(name="ekomek_common.publish_outbox")
def publish_outbox(batch_size=100):
    from django.db import connection, transaction

    from ekomek_common.outbox_app.models import OutboxEvent

    with transaction.atomic():
        queryset = OutboxEvent.objects.filter(published_at__isnull=True)
        if connection.vendor == "postgresql":
            queryset = queryset.select_for_update(skip_locked=True)
        events = list(queryset[:batch_size])
        published = 0
        for event in events:
            try:
                publish_event_now(event.event_type, event.payload)
                event.published_at = timezone.now()
                event.publish_attempts += 1
                event.save(update_fields=["published_at", "publish_attempts"])
                published += 1
            except Exception:
                event.publish_attempts += 1
                event.save(update_fields=["publish_attempts"])
                logger.exception("outbox_publish_failed event=%s", event.id)
        return published


@shared_task(name="ekomek_common.handle_domain_event")
def handle_domain_event(event_type, payload):
    from django.conf import settings

    handlers = getattr(settings, "EVENT_HANDLERS", {})
    handler = handlers.get(event_type)
    if handler is None:
        logger.info("event_ignored type=%s", event_type)
        return
    handler(payload)


def new_event_id():
    return str(uuid.uuid4())
