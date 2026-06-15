from django.conf import settings
from django.db import models
from apps.cards.models import FundraisingCard


class ModerationLog(models.Model):
    card = models.ForeignKey(FundraisingCard, on_delete=models.CASCADE, related_name="moderation_logs")
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=64)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} @ {self.card_id}"


class RedistributionDecision(models.Model):
    class DecisionType(models.TextChoices):
        REFUND = "refund", "Вернуть донорам"
        TRANSFER = "transfer", "Перераспределить на другой сбор"
        FUND = "fund", "Передать в общий фонд"
        HOLD = "hold", "Оставить до завершения проверки"

    card = models.ForeignKey(FundraisingCard, on_delete=models.CASCADE, related_name="redistributions")
    decision_type = models.CharField(max_length=16, choices=DecisionType.choices)
    target_card = models.ForeignKey(
        FundraisingCard, on_delete=models.SET_NULL, null=True, blank=True, related_name="incoming_redistributions"
    )
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.decision_type} ({self.card_id})"
