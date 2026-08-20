from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import sys

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ekomek_common.constants import CardStatus, UserStatus
from ekomek_common.http import ServiceClientError, cards_client, identity_client

from .adapters import get_delivery_adapter
from .models import Notification, NotificationDelivery, NotificationDeliveryLog

SAFE_PAYLOAD_BLOCKLIST = {
    "email",
    "phone",
    "iin",
    "iin_hash",
    "iin_masked",
    "cms",
    "contact_email",
    "contact_phone",
}
PROGRESS_MILESTONES = (75, 90, 100)


def safe_payload(payload):
    return {
        key: value
        for key, value in (payload or {}).items()
        if key not in SAFE_PAYLOAD_BLOCKLIST
    }


def _fetch_user(user_id):
    if not user_id:
        return None
    try:
        return identity_client().get(f"/internal/users/{user_id}/")
    except ServiceClientError:
        return None


def _fetch_card(card_id):
    if not card_id:
        return None
    try:
        return cards_client().get(f"/internal/cards/{card_id}/")
    except ServiceClientError:
        return None


def _as_decimal(value):
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def notification_deep_link(notification_type, payload):
    card_id = payload.get("card_id")
    expense_id = payload.get("expense_id")
    invoice_id = payload.get("invoice_id")
    payout_id = payload.get("payout_id")
    case_id = payload.get("case_id")
    if notification_type.startswith("card.") and card_id:
        return f"/author/cards/{card_id}"
    if notification_type.startswith("payment."):
        return "/donor"
    if notification_type.startswith("expense.") and expense_id and card_id:
        return f"/author/cards/{card_id}"
    if notification_type.startswith("document.") and card_id:
        return f"/author/cards/{card_id}"
    if notification_type.startswith("invoice.") and invoice_id and card_id:
        return f"/author/cards/{card_id}"
    if notification_type.startswith("payout.") and payout_id and card_id:
        return f"/author/cards/{card_id}"
    if notification_type.startswith("review.") and case_id:
        return f"/moderator/reviews/{case_id}"
    if notification_type.startswith("representation."):
        return "/profile"
    if notification_type.startswith("user."):
        return "/profile"
    if notification_type == "report.resolved" and card_id:
        return f"/cards/{card_id}"
    return payload.get("deep_link", "")


def delivery_destinations(recipient_id, payload):
    user = _fetch_user(recipient_id) or {}
    return {
        Notification.DeliveryChannel.EMAIL: payload.get("email") or user.get("email") or "",
        Notification.DeliveryChannel.SMS: payload.get("phone") or "",
        Notification.DeliveryChannel.PUSH: payload.get("push_token") or "",
    }


def queue_delivery(delivery_id):
    from .tasks import send_notification_delivery

    if "test" in sys.argv:
        return None
    try:
        send_notification_delivery.delay(delivery_id)
    except Exception:
        return None


@transaction.atomic
def create_notification(
    *,
    recipient_id,
    title,
    body,
    notification_type,
    event_type="",
    payload=None,
    deep_link="",
    idempotency_key="",
):
    if not recipient_id or not idempotency_key:
        return None
    notification, created = Notification.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "recipient_id": recipient_id,
            "title": title,
            "body": body,
            "notification_type": notification_type,
            "event_type": event_type or notification_type,
            "payload": safe_payload(payload),
            "deep_link": deep_link or notification_deep_link(notification_type, payload or {}),
        },
    )
    if not created:
        return notification
    for channel, destination in delivery_destinations(recipient_id, payload or {}).items():
        if not destination:
            NotificationDelivery.objects.create(
                notification=notification,
                channel=channel,
                status=NotificationDelivery.Status.SKIPPED,
                last_error="Missing destination",
            )
            continue
        delivery = NotificationDelivery.objects.create(
            notification=notification,
            channel=channel,
            status=NotificationDelivery.Status.PENDING,
            destination=destination,
        )
        queue_delivery(delivery.id)
    return notification


def mark_notification_read(notification):
    if notification.is_read:
        return notification
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save(update_fields=("is_read", "read_at"))
    return notification


def mark_notification_unread(notification):
    if not notification.is_read:
        return notification
    notification.is_read = False
    notification.read_at = None
    notification.save(update_fields=("is_read", "read_at"))
    return notification


def delivery_backoff(attempt_count):
    return timezone.now() + timedelta(minutes=min(60, 2 ** max(attempt_count - 1, 0)))


@transaction.atomic
def send_delivery(delivery):
    delivery = NotificationDelivery.objects.select_for_update().select_related("notification").get(pk=delivery.pk)
    if delivery.status in (NotificationDelivery.Status.SENT, NotificationDelivery.Status.SKIPPED):
        return delivery
    notification = delivery.notification
    adapter = get_delivery_adapter(delivery.channel)
    delivery.attempt_count += 1
    delivery.last_attempt_at = timezone.now()
    try:
        result = adapter.send(
            destination=delivery.destination,
            title=notification.title,
            body=notification.body,
            payload=notification.payload,
        )
    except Exception as exc:
        max_attempts = getattr(settings, "NOTIFICATION_DELIVERY_MAX_ATTEMPTS", 3)
        delivery.last_error = str(exc)
        if delivery.attempt_count >= max_attempts:
            delivery.status = NotificationDelivery.Status.FAILED
            delivery.next_attempt_at = None
        else:
            delivery.status = NotificationDelivery.Status.RETRYING
            delivery.next_attempt_at = delivery_backoff(delivery.attempt_count)
        delivery.save(
            update_fields=(
                "attempt_count",
                "last_attempt_at",
                "last_error",
                "status",
                "next_attempt_at",
                "updated_at",
            )
        )
        NotificationDeliveryLog.objects.create(
            delivery=delivery,
            attempt_number=delivery.attempt_count,
            status=delivery.status,
            response_payload={},
            error_message=str(exc),
        )
        return delivery
    delivery.provider = result.provider
    delivery.provider_message_id = result.provider_message_id
    delivery.last_error = ""
    delivery.status = NotificationDelivery.Status.SENT
    delivery.next_attempt_at = None
    delivery.sent_at = timezone.now()
    delivery.delivered_at = delivery.sent_at
    delivery.save(
        update_fields=(
            "attempt_count",
            "last_attempt_at",
            "provider",
            "provider_message_id",
            "last_error",
            "status",
            "next_attempt_at",
            "sent_at",
            "delivered_at",
            "updated_at",
        )
    )
    NotificationDeliveryLog.objects.create(
        delivery=delivery,
        attempt_number=delivery.attempt_count,
        status=delivery.status,
        response_payload=result.response_payload,
        error_message="",
    )
    return delivery


def _create_user_notification(event_type, user_id, title, body, payload, suffix):
    return create_notification(
        recipient_id=user_id,
        title=title,
        body=body,
        notification_type=event_type,
        event_type=event_type,
        payload=payload,
        idempotency_key=f"{event_type}:{suffix}",
    )


def on_notification_requested(payload):
    idempotency_key = payload.get("idempotency_key") or (
        f"notification.requested:{payload.get('user_id')}:{payload.get('event_type', '')}:{payload.get('title', '')}"
    )
    return create_notification(
        recipient_id=payload.get("user_id"),
        title=payload.get("title", "Уведомление"),
        body=payload.get("body", ""),
        notification_type=payload.get("type") or payload.get("event_type", "notification.requested"),
        event_type=payload.get("event_type", "notification.requested"),
        payload=payload.get("payload") or {},
        deep_link=payload.get("deep_link", ""),
        idempotency_key=idempotency_key,
    )


def on_user_registered(payload):
    return _create_user_notification(
        "user.registered",
        payload.get("user_id"),
        "Регистрация завершена",
        "Ваш аккаунт создан. Следите за статусом проверки в профиле.",
        payload,
        payload.get("user_id"),
    )


def on_user_manual_review_required(payload):
    return _create_user_notification(
        "user.manual_review_required",
        payload.get("user_id"),
        "Аккаунт отправлен на ручную проверку",
        "Мы проверяем ваши данные вручную. Это может занять немного времени.",
        payload,
        payload.get("user_id"),
    )


def on_user_status_changed(payload):
    status = payload.get("status")
    user_id = payload.get("user_id")
    if status == UserStatus.ECP_VERIFIED:
        return _create_user_notification(
            "user.ecp_verified",
            user_id,
            "ЭЦП успешно подтверждена",
            "Подпись проверена. Теперь вы можете пользоваться полным функционалом платформы.",
            payload,
            f"{user_id}:{status}",
        )
    if status == UserStatus.REJECTED:
        return _create_user_notification(
            "user.rejected",
            user_id,
            "Проверка не пройдена",
            payload.get("reason") or "Мы не смогли подтвердить данные. Проверьте профиль и повторите попытку.",
            payload,
            f"{user_id}:{status}:{payload.get('reason', '')}",
        )
    if status == UserStatus.BLOCKED:
        return _create_user_notification(
            "user.blocked",
            user_id,
            "Доступ ограничен",
            payload.get("reason") or "Аккаунт временно ограничен. Обратитесь в поддержку, если это ошибка.",
            payload,
            f"{user_id}:{status}:{payload.get('reason', '')}",
        )
    if status == UserStatus.MANUAL_REVIEW:
        return _create_user_notification(
            "user.manual_review",
            user_id,
            "Требуется ручная проверка",
            payload.get("reason") or "Ваш аккаунт проверяется вручную.",
            payload,
            f"{user_id}:{status}:{payload.get('reason', '')}",
        )
    return None


def on_card_submitted(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    return _create_user_notification(
        "card.submitted",
        card.get("author_id") or payload.get("author_id"),
        "Сбор отправлен на модерацию",
        "Ваша карточка отправлена на проверку.",
        {**payload, "card_id": payload.get("card_id")},
        payload.get("card_id"),
    )


def on_card_manual_review_required(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    return _create_user_notification(
        "card.manual_review_required",
        card.get("author_id"),
        "Сбор проверяется вручную",
        "Для вашего сбора требуется дополнительная ручная проверка.",
        payload,
        payload.get("card_id"),
    )


def on_card_status_changed(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    author_id = card.get("author_id")
    status = payload.get("status")
    if status == CardStatus.ACTIVE:
        return _create_user_notification(
            "card.approved",
            author_id,
            "Сбор одобрен",
            "Сбор прошёл модерацию и опубликован.",
            payload,
            f"{payload.get('card_id')}:{status}",
        )
    if status == CardStatus.REJECTED:
        return _create_user_notification(
            "card.rejected",
            author_id,
            "Сбор отклонён",
            "Сбор не прошёл модерацию. Проверьте замечания и обновите данные при необходимости.",
            payload,
            f"{payload.get('card_id')}:{status}",
        )
    return None


def on_card_revision_required(payload):
    return _create_user_notification(
        "card.revision_required",
        payload.get("author_id"),
        "Нужна доработка сбора",
        payload.get("revision_comment") or "Модератор указал, что нужно исправить в карточке сбора.",
        payload,
        payload.get("card_id"),
    )


def on_card_suspended(payload):
    return _create_user_notification(
        "card.suspended",
        payload.get("author_id"),
        "Сбор приостановлен",
        payload.get("reason") or "Ваш сбор временно приостановлен модерацией.",
        payload,
        f"{payload.get('card_id')}:{payload.get('reason', '')}",
    )


def on_card_unsuspended(payload):
    return _create_user_notification(
        "card.unsuspended",
        payload.get("author_id"),
        "Приостановка снята",
        payload.get("reason") or "Сбор снова доступен после проверки.",
        payload,
        f"{payload.get('card_id')}:{payload.get('restored_status', '')}",
    )


def on_document_revision_required(payload):
    return _create_user_notification(
        "document.revision_required",
        payload.get("author_id"),
        "Нужна доработка документа",
        payload.get("revision_comment") or "Модератор попросил обновить документ.",
        payload,
        payload.get("document_id"),
    )


def on_document_expired(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    return _create_user_notification(
        "document.expired",
        card.get("author_id"),
        "Документ истёк",
        "Один из документов по сбору истёк. Загрузите актуальную версию.",
        payload,
        payload.get("document_id"),
    )


def on_expense_revision_required(payload):
    return _create_user_notification(
        "expense.revision_required",
        payload.get("author_id"),
        "Нужна доработка расхода",
        payload.get("revision_comment") or "Модератор указал, что нужно исправить в расходе.",
        payload,
        payload.get("expense_id"),
    )


def on_expense_approved(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    return _create_user_notification(
        "expense.approved",
        card.get("author_id"),
        "Расход подтверждён",
        "Расход одобрен и добавлен в отчёт по сбору.",
        payload,
        payload.get("expense_id"),
    )


def on_expense_rejected(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    return _create_user_notification(
        "expense.rejected",
        card.get("author_id"),
        "Расход отклонён",
        "Расход не прошёл проверку. Исправьте данные и отправьте снова при необходимости.",
        payload,
        payload.get("expense_id"),
    )


def on_invoice_verified(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    return _create_user_notification(
        "invoice.verified",
        card.get("author_id"),
        "Счёт подтверждён",
        "Счёт клиники подтверждён, выплата будет обработана отдельно.",
        payload,
        payload.get("invoice_id"),
    )


def on_invoice_rejected(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    return _create_user_notification(
        "invoice.rejected",
        card.get("author_id"),
        "Счёт отклонён",
        payload.get("reason") or "Счёт не прошёл проверку. Загрузите исправленную версию.",
        payload,
        payload.get("invoice_id"),
    )


def on_payout_succeeded(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    return _create_user_notification(
        "payout.succeeded",
        card.get("author_id"),
        "Выплата выполнена",
        "Средства по подтверждённому счёту успешно переведены.",
        payload,
        payload.get("payout_id"),
    )


def on_payout_failed(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    return _create_user_notification(
        "payout.failed",
        card.get("author_id"),
        "Выплата не выполнена",
        "Не удалось завершить выплату. Мы повторим попытку или свяжемся с вами при необходимости.",
        payload,
        payload.get("payout_id"),
    )


def on_report_resolved(payload):
    return _create_user_notification(
        "report.resolved",
        payload.get("reporter_user_id"),
        "Жалоба рассмотрена",
        payload.get("resolution") or "Модератор обработал вашу жалобу.",
        payload,
        payload.get("report_id"),
    )


def on_representation_submitted(payload):
    return _create_user_notification(
        "representation.submitted",
        payload.get("author_id"),
        "Представительство отправлено на проверку",
        "Запрос на подтверждение представительства принят и ожидает решения.",
        payload,
        payload.get("representation_id"),
    )


def on_representation_rejected(payload):
    return _create_user_notification(
        "representation.rejected",
        payload.get("author_id"),
        "Представительство отклонено",
        payload.get("reason") or "Подтверждение представительства не прошло проверку.",
        payload,
        payload.get("representation_id"),
    )


def on_review_opened(payload):
    if payload.get("subject_type") == "user":
        return create_notification(
            recipient_id=payload.get("subject_id"),
            title="Открыта ручная проверка",
            body="По вашему профилю начата дополнительная ручная проверка.",
            notification_type="review.opened",
            event_type="review.opened",
            payload=payload,
            deep_link="/profile",
            idempotency_key=f"review.opened:user:{payload.get('case_id')}",
        )
    if payload.get("subject_type") == "card":
        card = _fetch_card(payload.get("subject_id")) or {}
        return create_notification(
            recipient_id=card.get("author_id"),
            title="Сбор направлен на ручную проверку",
            body="По вашему сбору открыта дополнительная ручная проверка.",
            notification_type="review.opened",
            event_type="review.opened",
            payload=payload,
            deep_link=f"/author/cards/{payload.get('subject_id')}",
            idempotency_key=f"review.opened:card:{payload.get('case_id')}",
        )
    return None


def on_review_decision_applied(payload):
    if payload.get("subject_type") == "user":
        return create_notification(
            recipient_id=payload.get("subject_id"),
            title="Принято решение по проверке",
            body="По вашему профилю применено решение модератора.",
            notification_type="review.decision_applied",
            event_type="review.decision_applied",
            payload=payload,
            deep_link="/profile",
            idempotency_key=f"review.decision_applied:user:{payload.get('case_id')}:{payload.get('action')}",
        )
    if payload.get("subject_type") == "card":
        card = _fetch_card(payload.get("subject_id")) or {}
        return create_notification(
            recipient_id=card.get("author_id"),
            title="Принято решение по сбору",
            body="По вашему сбору применено решение модератора.",
            notification_type="review.decision_applied",
            event_type="review.decision_applied",
            payload=payload,
            deep_link=f"/author/cards/{payload.get('subject_id')}",
            idempotency_key=f"review.decision_applied:card:{payload.get('case_id')}:{payload.get('action')}",
        )
    return None


def on_payment_succeeded(payload):
    card = _fetch_card(payload.get("card_id")) or {}
    author_id = card.get("author_id")
    create_notification(
        recipient_id=author_id,
        title="Новое пожертвование",
        body=f"На ваш сбор поступило пожертвование на {payload.get('amount')} {payload.get('currency', 'KZT')}.",
        notification_type="payment.succeeded",
        event_type="payment.succeeded",
        payload=payload,
        idempotency_key=f"payment.succeeded:{payload.get('donation_id')}",
    )
    target_amount = _as_decimal(card.get("target_amount"))
    collected_amount = _as_decimal(card.get("collected_amount"))
    if target_amount <= 0:
        return None
    progress = int((collected_amount / target_amount) * Decimal("100"))
    for milestone in PROGRESS_MILESTONES:
        if progress < milestone:
            continue
        create_notification(
            recipient_id=author_id,
            title=f"Собрано {milestone}%",
            body=f"Сбор достиг отметки {milestone}% от целевой суммы.",
            notification_type="fundraising.progress",
            event_type="payment.succeeded",
            payload={**payload, "milestone": milestone, "progress_percent": progress},
            idempotency_key=f"fundraising.progress:{payload.get('card_id')}:{milestone}",
        )
    return None


def on_payment_failed(payload):
    donor_id = payload.get("donor_id")
    if not donor_id:
        return None
    return create_notification(
        recipient_id=donor_id,
        title="Платёж не завершён",
        body=payload.get("reason") or "Не удалось завершить платёж. Попробуйте снова или выберите другой способ оплаты.",
        notification_type="payment.failed",
        event_type="payment.failed",
        payload=payload,
        idempotency_key=f"payment.failed:{payload.get('donation_id')}:{payload.get('status')}",
    )


def notify_upcoming_deadline(card):
    days_left = max((date.fromisoformat(str(card["end_date"])[:10]) - timezone.localdate()).days, 0)
    return create_notification(
        recipient_id=card.get("author_id"),
        title="Срок сбора скоро завершится",
        body=f"До окончания сбора осталось {days_left} дн.",
        notification_type="card.deadline_approaching",
        event_type="card.deadline_approaching",
        payload={"card_id": card.get("id"), "end_date": card.get("end_date"), "days_left": days_left},
        idempotency_key=f"card.deadline_approaching:{card.get('id')}:{card.get('end_date')}",
    )


EVENT_HANDLERS = {
    "notification.requested": on_notification_requested,
    "user.registered": on_user_registered,
    "user.manual_review_required": on_user_manual_review_required,
    "user.status_changed": on_user_status_changed,
    "card.submitted": on_card_submitted,
    "card.manual_review_required": on_card_manual_review_required,
    "card.status_changed": on_card_status_changed,
    "card.revision_required": on_card_revision_required,
    "card.suspended": on_card_suspended,
    "card.unsuspended": on_card_unsuspended,
    "payment.succeeded": on_payment_succeeded,
    "payment.failed": on_payment_failed,
    "expense.approved": on_expense_approved,
    "expense.rejected": on_expense_rejected,
    "expense.revision_required": on_expense_revision_required,
    "document.expired": on_document_expired,
    "document.revision_required": on_document_revision_required,
    "invoice.verified": on_invoice_verified,
    "invoice.rejected": on_invoice_rejected,
    "payout.succeeded": on_payout_succeeded,
    "payout.failed": on_payout_failed,
    "report.resolved": on_report_resolved,
    "representation.submitted": on_representation_submitted,
    "representation.rejected": on_representation_rejected,
    "review.opened": on_review_opened,
    "review.decision_applied": on_review_decision_applied,
}
