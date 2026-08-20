from django.db import transaction
from django.db.models import F

from ekomek_common.constants import UserStatus
from ekomek_common.http import ServiceClientError, verification_client
from ekomek_common.outbox import enqueue_event

from .models import BalanceTransaction, BalanceTransactionType, User


class BalanceError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def is_author_blocked_by_antifraud(iin):
    try:
        payload = verification_client().post("/internal/antifraud/lookup/", json={"iin": iin})
    except ServiceClientError as exc:
        if exc.status_code == 404:
            return False
        return False
    return bool(payload and payload.get("blocked"))


@transaction.atomic
def credit_user_balance(user, amount, description="", purpose=""):
    if purpose == "donor_refund":
        raise BalanceError("Возврат донорам отключён.")
    if amount <= 0:
        return user
    User.objects.filter(pk=user.pk).update(balance=F("balance") + amount)
    BalanceTransaction.objects.create(
        user=user,
        amount=amount,
        transaction_type=BalanceTransactionType.REFUND_IN,
        description=description,
    )
    user.refresh_from_db()
    return user


@transaction.atomic
def withdraw_user_balance(user, amount):
    if amount <= 0:
        raise BalanceError("Сумма вывода должна быть больше нуля.")
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.balance < amount:
        raise BalanceError("Недостаточно средств на балансе.")
    User.objects.filter(pk=user.pk).update(balance=F("balance") - amount)
    transaction_record = BalanceTransaction.objects.create(
        user=user,
        amount=amount,
        transaction_type=BalanceTransactionType.WITHDRAW_OUT,
        description="Заявка на вывод принята",
    )
    user.refresh_from_db()
    return user, transaction_record


@transaction.atomic
def register_user(user):
    payload = identity_event_payload(user)
    enqueue_event("user.registered", "user", user.id, payload)
    if user.status == UserStatus.MANUAL_REVIEW:
        enqueue_event("user.manual_review_required", "user", user.id, payload)
    return user


def set_user_status(user, new_status, reason=""):
    if user.status == new_status:
        return user
    previous = user.status
    user.status = new_status
    user.save(update_fields=["status", "updated_at"])
    payload = identity_event_payload(user, {"previous_status": previous, "reason": reason})
    enqueue_event("user.status_changed", "user", user.id, payload)
    if new_status == UserStatus.BLOCKED:
        enqueue_event("user.blocked", "user", user.id, payload)
    return user


def identity_event_payload(user, extra=None):
    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "status": user.status,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "iin_hash": user.iin_hash,
        "iin_masked": user.iin_masked,
        "ecp_verification_id": user.ecp_verification_id,
        "ecp_locked_fields": user.ecp_locked_fields,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }
    if extra:
        payload.update(extra)
    return payload


def apply_identity_corrections(user, data, actor="admin"):
    if "full_name" in data:
        user.full_name = data["full_name"]
    if "birth_date" in data:
        user.birth_date = data["birth_date"]
    user.save()
    enqueue_event(
        "user.updated",
        "user",
        user.id,
        identity_event_payload(user, {"actor": actor, "fields": sorted(data.keys())}),
    )
    return user
