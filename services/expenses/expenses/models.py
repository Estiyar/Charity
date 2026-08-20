import uuid

from django.db import models

from .storage import private_expense_storage


def original_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"expenses/original/{instance.card_id}/{uuid.uuid4().hex}.{extension}"


def public_upload_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return f"expenses/public/{instance.card_id}/{uuid.uuid4().hex}.{extension}"


class ExpenseStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    SUBMITTED = "submitted", "Отправлен"
    PENDING_REVIEW = "pending_review", "На проверке"
    REVISION_REQUIRED = "revision_required", "На доработке"
    APPROVED = "approved", "Подтверждён"
    REJECTED = "rejected", "Отклонён"
    PAID = "paid", "Оплачен"
    CANCELED = "canceled", "Отменён"


class ExpenseCategory(models.TextChoices):
    MEDICINE = "medicine", "Лекарства"
    TREATMENT = "treatment", "Лечение"
    CLINIC = "clinic", "Клиника"
    TRANSPORT = "transport", "Транспорт"
    LIVING = "living", "Проживание"
    OTHER = "other", "Другое"


class LedgerEntryType(models.TextChoices):
    DONATION = "donation", "Пожертвование"
    EXPENSE = "expense", "Подтверждённый расход"
    PAYOUT = "payout", "Прямая выплата"
    REDISTRIBUTION_OUT = "redistribution_out", "Перераспределение исходящее"
    REDISTRIBUTION_IN = "redistribution_in", "Перераспределение входящее"
    CORRECTION = "correction", "Корректировка"


class Expense(models.Model):
    card_id = models.IntegerField(db_index=True)
    card_name = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    category = models.CharField(max_length=32, choices=ExpenseCategory.choices, default=ExpenseCategory.OTHER)
    purpose = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    comment = models.TextField(blank=True)
    original_file = models.FileField(
        upload_to=original_upload_path,
        storage=private_expense_storage,
        null=True,
        blank=True,
    )
    public_file = models.FileField(upload_to=public_upload_path, null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=ExpenseStatus.choices, default=ExpenseStatus.DRAFT)
    submitted_by_id = models.IntegerField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    moderator_comment = models.TextField(blank=True)
    publish_receipt = models.BooleanField(default=True)
    payout_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_expense"
        ordering = ["-created_at"]

    @property
    def description(self):
        return self.comment or self.purpose


class ExpenseDecisionEvent(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="decisions")
    action = models.CharField(max_length=32, db_index=True)
    reason = models.TextField(blank=True)
    actor_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses_expensedecisionevent"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Решение по расходу неизменяемо.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Решение по расходу неизменяемо.")


class LedgerEntry(models.Model):
    card_id = models.IntegerField(db_index=True)
    entry_type = models.CharField(max_length=32, choices=LedgerEntryType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="KZT")
    source_type = models.CharField(max_length=32)
    source_id = models.CharField(max_length=64)
    idempotency_key = models.CharField(max_length=128, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses_ledgerentry"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Проводка неизменяема.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Проводка неизменяема.")


class ReconciliationReport(models.Model):
    card_id = models.IntegerField(db_index=True)
    matched = models.BooleanField(default=False)
    differences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses_reconciliationreport"
        ordering = ["-created_at"]


from .payout_models import (  # noqa: E402,F401
    Invoice,
    InvoiceDecisionEvent,
    InvoiceStatus,
    OrganizationKind,
    OrganizationStatus,
    OrganizationVerificationEvent,
    Payout,
    PayoutEvent,
    PayoutStatus,
    ProcessedPayoutCallback,
    VerifiedOrganization,
)
from .comment_models import ExpenseCommentEdit, ExpenseModeratorComment  # noqa: E402,F401
