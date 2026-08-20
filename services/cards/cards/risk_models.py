from django.db import models, transaction
from django.utils import timezone

from ekomek_common.risk import RiskLevel


class RiskAssessment(models.Model):
    card_id = models.IntegerField(db_index=True)
    risk_score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=16, choices=RiskLevel.CHOICES, default=RiskLevel.LOW)
    factors = models.JSONField(default=list)
    config_version = models.CharField(max_length=32, blank=True)
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cards_risk_assessment"
        ordering = ["-calculated_at"]
        indexes = [
            models.Index(fields=["card_id", "-calculated_at"]),
        ]

    @classmethod
    def latest_for_card(cls, card_id):
        return cls.objects.filter(card_id=card_id).order_by("-calculated_at", "-id").first()


class RiskOverride(models.Model):
    card_id = models.IntegerField(db_index=True)
    moderator_id = models.IntegerField()
    moderator_name = models.CharField(max_length=255, blank=True)
    previous_score = models.PositiveSmallIntegerField(default=0)
    previous_level = models.CharField(max_length=16, blank=True)
    new_score = models.PositiveSmallIntegerField(default=0)
    new_level = models.CharField(max_length=16, blank=True)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cards_risk_override"
        ordering = ["-created_at"]
