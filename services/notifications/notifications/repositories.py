from django.db.models import Q
from django.utils import timezone

from .models import Notification, NotificationDelivery


class NotificationRepository:
    def for_recipient(self, recipient_id, *, unread=None, notification_type=""):
        queryset = Notification.objects.filter(recipient_id=recipient_id).prefetch_related("deliveries__logs")
        if unread is True:
            queryset = queryset.filter(is_read=False)
        elif unread is False:
            queryset = queryset.filter(is_read=True)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        return queryset

    def unread_count(self, recipient_id):
        return Notification.objects.filter(recipient_id=recipient_id, is_read=False).count()

    def mark_all_read(self, recipient_id):
        now = timezone.now()
        return Notification.objects.filter(recipient_id=recipient_id, is_read=False).update(
            is_read=True,
            read_at=now,
        )


class NotificationDeliveryRepository:
    def due(self, now=None):
        now = now or timezone.now()
        return NotificationDelivery.objects.filter(
            Q(status=NotificationDelivery.Status.PENDING)
            | Q(status=NotificationDelivery.Status.RETRYING, next_attempt_at__lte=now)
        ).select_related("notification")
