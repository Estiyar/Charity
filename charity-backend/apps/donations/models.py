from django.conf import settings
from django.db import models
from apps.cards.models import FundraisingCard


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Ожидает"
    SUCCESS = "success", "Успешно"
    FAILED = "failed", "Ошибка"


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
