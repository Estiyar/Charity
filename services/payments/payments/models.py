from django.db import models


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    PROCESSING = "processing", "Обработка"
    SUCCESS = "success", "Успешно"
    FAILED = "failed", "Ошибка"
    CANCELED = "canceled", "Отменён"
    REFUNDED_DISABLED = "refunded_disabled", "Возврат отключён"


class LedgerEntryType(models.TextChoices):
    DONATION_CREDIT = "donation_credit", "Зачисление пожертвования"


class RefundChoice(models.TextChoices):
    EMPTY = "empty", "Не выбрано"
    KEEP = "keep", "Оставить семье"
    HOLD = "hold", "Оставить на карточке до проверки"
    REFUND = "refund", "Возврат (legacy)"
    REDIRECT = "redirect", "Перенаправить"


class RefundDecisionStatus(models.TextChoices):
    PENDING = "pending", "Ожидает решения"
    DONE = "done", "Выполнено"
    EXPIRED = "expired", "Истёк срок"


class Donation(models.Model):
    card_id = models.IntegerField(db_index=True)
    card_name = models.CharField(max_length=255, blank=True)
    donor_id = models.IntegerField(null=True, blank=True, db_index=True)
    donor_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="KZT")
    payment_status = models.CharField(
        max_length=24, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    payment_method = models.CharField(max_length=64, blank=True)
    provider = models.CharField(max_length=32, blank=True)
    provider_payment_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    idempotency_key = models.CharField(max_length=64, unique=True)
    redirect_url = models.TextField(blank=True)
    failed_reason = models.TextField(blank=True)
    collected_applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_donation"


class PaymentEvent(models.Model):
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=32)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments_paymentevent"
        ordering = ["id"]


class LedgerEntry(models.Model):
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name="ledger_entries")
    card_id = models.IntegerField(db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="KZT")
    entry_type = models.CharField(max_length=32, choices=LedgerEntryType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments_ledgerentry"
        constraints = [
            models.UniqueConstraint(
                fields=["donation", "entry_type"],
                name="unique_ledger_entry_per_donation_type",
            ),
        ]


class ProcessedProviderEvent(models.Model):
    provider = models.CharField(max_length=32)
    event_key = models.CharField(max_length=160)
    payload = models.JSONField(default=dict, blank=True)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments_processedproviderevent"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_key"],
                name="unique_processed_provider_event",
            ),
        ]


class RefundDecision(models.Model):
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name="refund_decisions")
    card_id = models.IntegerField(db_index=True)
    card_snapshot = models.JSONField(default=dict)
    donor_id = models.IntegerField(db_index=True)
    share_amount = models.DecimalField(max_digits=14, decimal_places=2)
    choice = models.CharField(max_length=16, choices=RefundChoice.choices, default=RefundChoice.EMPTY)
    status = models.CharField(
        max_length=16, choices=RefundDecisionStatus.choices, default=RefundDecisionStatus.PENDING
    )
    target_card_id = models.IntegerField(null=True, blank=True)
    target_card_snapshot = models.JSONField(default=dict, blank=True)
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments_refunddecision"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["donation", "card_id"], name="unique_refund_decision_per_donation_card"),
        ]
