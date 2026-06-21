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
