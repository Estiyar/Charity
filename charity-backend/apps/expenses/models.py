from django.db import models
from apps.cards.models import FundraisingCard


class ExpenseStatus(models.TextChoices):
    PENDING = "pending", "На проверке"
    APPROVED = "approved", "Подтверждён"
    REJECTED = "rejected", "Отклонён"


class Expense(models.Model):
    card = models.ForeignKey(FundraisingCard, on_delete=models.CASCADE, related_name="expenses")
    date = models.DateField()
    purpose = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    comment = models.TextField(blank=True)
    document_url = models.FileField(upload_to="cards/expenses/", null=True, blank=True)
    status = models.CharField(max_length=16, choices=ExpenseStatus.choices, default=ExpenseStatus.PENDING)
    moderator_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.purpose} — {self.amount} ({self.status})"
