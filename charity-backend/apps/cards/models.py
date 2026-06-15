from django.conf import settings
from django.db import models

from apps.common.card_status import CardStatus, PUBLIC_STATUSES
from apps.common.masking import mask_iin, mask_document_number, mask_phone


class Gender(models.TextChoices):
    MALE = "male", "Мужской"
    FEMALE = "female", "Женский"


class City(models.Model):
    """Справочник городов (ТЗ раздел 24)."""
    name = models.CharField(max_length=128, unique=True)

    class Meta:
        verbose_name_plural = "Cities"

    def __str__(self):
        return self.name


class Diagnosis(models.Model):
    """Справочник диагнозов/болезней (ТЗ раздел 24)."""
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = "Diagnoses"

    def __str__(self):
        return self.name


class FundraisingCard(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cards"
    )

    # Данные получателя (ТЗ раздел 7)
    full_name = models.CharField(max_length=255)
    diagnosis = models.CharField(max_length=255)
    city = models.CharField(max_length=128)
    clinic = models.CharField(max_length=255, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=8, choices=Gender.choices, blank=True)
    description = models.TextField(blank=True)

    photo_url = models.ImageField(upload_to="cards/photos/", null=True, blank=True)

    # Суммы
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    collected_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    end_date = models.DateField()

    status = models.CharField(
        max_length=32, choices=CardStatus.choices, default=CardStatus.DRAFT
    )

    # Конфиденциальные данные: храним полное (скрытое) + маскированное (ТЗ раздел 8, 26)
    iin_encrypted = models.CharField(max_length=64, blank=True)
    iin_masked = models.CharField(max_length=32, blank=True)
    document_number_encrypted = models.CharField(max_length=64, blank=True)
    document_number_masked = models.CharField(max_length=32, blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    contact_email = models.EmailField(blank=True)

    moderator_comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Автоматически пересчитываем маски при сохранении
        if self.iin_encrypted:
            self.iin_masked = mask_iin(self.iin_encrypted)
        if self.document_number_encrypted:
            self.document_number_masked = mask_document_number(self.document_number_encrypted)
        super().save(*args, **kwargs)

    @property
    def is_public(self):
        return self.status in PUBLIC_STATUSES

    @property
    def masked_phone(self):
        return mask_phone(self.contact_phone)

    @property
    def progress_percent(self):
        if not self.target_amount:
            return 0
        return min(100, round(float(self.collected_amount) / float(self.target_amount) * 100, 1))

    # --- Эскроу-баланс (ТЗ раздел 18), считается по каждой карточке отдельно ---
    @property
    def escrow_received(self):
        return self.collected_amount

    @property
    def escrow_spent(self):
        from apps.expenses.models import Expense, ExpenseStatus
        total = self.expenses.filter(status=ExpenseStatus.APPROVED).aggregate(
            s=models.Sum("amount")
        )["s"]
        return total or 0

    @property
    def escrow_pending(self):
        from apps.expenses.models import Expense, ExpenseStatus
        total = self.expenses.filter(status=ExpenseStatus.PENDING).aggregate(
            s=models.Sum("amount")
        )["s"]
        return total or 0

    @property
    def escrow_available(self):
        return float(self.escrow_received) - float(self.escrow_spent) - float(self.escrow_pending)

    @property
    def escrow_balance(self):
        return float(self.escrow_received) - float(self.escrow_spent)

    def __str__(self):
        return f"{self.full_name} — {self.status}"
