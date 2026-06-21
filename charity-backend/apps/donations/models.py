from django.conf import settings
from django.db import models

from apps.cards.models import FundraisingCard


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    SUCCESS = "success", "Успешно"
    FAILED = "failed", "Ошибка"


class RefundChoice(models.TextChoices):
    EMPTY = "empty", "Не выбрано"
    KEEP = "keep", "Оставить семье"
    REFUND = "refund", "Возврат"
    REDIRECT = "redirect", "Перенаправить"


class RefundDecisionStatus(models.TextChoices):
    PENDING = "pending", "Ожидает решения"
    DONE = "done", "Выполнено"
    EXPIRED = "expired", "Истёк срок"


class Donation(models.Model):
    card = models.ForeignKey(FundraisingCard, on_delete=models.CASCADE, related_name="donations")
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="donations"
    )
    donor_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.SUCCESS)
    payment_method = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.donor_name} — {self.amount}"


class RefundDecision(models.Model):
    donation = models.ForeignKey(
        Donation,
        on_delete=models.CASCADE,
        related_name="refund_decisions",
    )
    card = models.ForeignKey(
        FundraisingCard,
        on_delete=models.CASCADE,
        related_name="refund_decisions",
    )
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refund_decisions",
    )
    share_amount = models.DecimalField(max_digits=14, decimal_places=2)
    choice = models.CharField(
        max_length=16,
        choices=RefundChoice.choices,
        default=RefundChoice.EMPTY,
    )
    status = models.CharField(
        max_length=16,
        choices=RefundDecisionStatus.choices,
        default=RefundDecisionStatus.PENDING,
    )
    target_card = models.ForeignKey(
        FundraisingCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_refund_decisions",
    )
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["donation", "card"],
                name="unique_refund_decision_per_donation_card",
            ),
        ]

    def __str__(self):
        return f"RefundDecision #{self.pk} — {self.donor_id} @ card {self.card_id}"
