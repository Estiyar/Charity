from decimal import Decimal
import uuid

from django.db import models

from .storage import private_expense_storage


def invoice_original_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"invoices/original/{instance.card_id}/{uuid.uuid4().hex}.{extension}"


def invoice_public_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    return f"invoices/public/{instance.card_id}/{uuid.uuid4().hex}.{extension}"


class OrganizationStatus(models.TextChoices):
    PENDING = "pending", "Ожидает проверки"
    VERIFIED = "verified", "Подтверждена"
    REJECTED = "rejected", "Отклонена"


class OrganizationKind(models.TextChoices):
    CLINIC = "clinic", "Клиника"
    SUPPLIER = "supplier", "Поставщик"


class InvoiceStatus(models.TextChoices):
    PENDING_VERIFICATION = "pending_verification", "Ожидает проверки"
    VERIFIED = "verified", "Подтверждён"
    REJECTED = "rejected", "Отклонён"
    PARTIALLY_PAID = "partially_paid", "Частично оплачен"
    PAID = "paid", "Оплачен"
    CANCELED = "canceled", "Отменён"


class PayoutStatus(models.TextChoices):
    REQUESTED = "requested", "Запрошена"
    PROCESSING = "processing", "В обработке"
    SUCCEEDED = "succeeded", "Выполнена"
    FAILED = "failed", "Ошибка"
    CANCELED = "canceled", "Отменена"


class VerifiedOrganization(models.Model):
    name = models.CharField(max_length=255)
    kind = models.CharField(max_length=32, choices=OrganizationKind.choices, default=OrganizationKind.CLINIC)
    bin_hash = models.CharField(max_length=64, unique=True)
    bin_masked = models.CharField(max_length=32)
    bin_encrypted = models.TextField()
    iban_masked = models.CharField(max_length=32)
    iban_encrypted = models.TextField()
    bank_name = models.CharField(max_length=255, blank=True)
    verification_status = models.CharField(
        max_length=32, choices=OrganizationStatus.choices, default=OrganizationStatus.PENDING
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by_id = models.IntegerField(null=True, blank=True)
    verification_reason = models.TextField(blank=True)
    created_by_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_verifiedorganization"
        ordering = ["name"]


class OrganizationVerificationEvent(models.Model):
    organization = models.ForeignKey(VerifiedOrganization, on_delete=models.CASCADE, related_name="verifications")
    action = models.CharField(max_length=32, db_index=True)
    reason = models.TextField(blank=True)
    actor_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses_organizationverificationevent"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Проверка организации неизменяема.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Проверка организации неизменяема.")


class Invoice(models.Model):
    card_id = models.IntegerField(db_index=True)
    card_name = models.CharField(max_length=255, blank=True)
    organization = models.ForeignKey(VerifiedOrganization, on_delete=models.PROTECT, related_name="invoices")
    number = models.CharField(max_length=64, blank=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="KZT")
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=32, choices=InvoiceStatus.choices, default=InvoiceStatus.PENDING_VERIFICATION
    )
    original_file = models.FileField(
        upload_to=invoice_original_path,
        storage=private_expense_storage,
        null=True,
        blank=True,
    )
    public_file = models.FileField(upload_to=invoice_public_path, null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    submitted_by_id = models.IntegerField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    publish_receipt = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_invoice"
        ordering = ["-created_at"]

    @property
    def remaining_amount(self):
        leftover = self.amount - self.paid_amount
        return leftover if leftover > 0 else Decimal("0")

    @property
    def purpose(self):
        return f"Оплата {self.organization.get_kind_display().lower()}: {self.organization.name}"

    @property
    def payee_name(self):
        return self.organization.name


class InvoiceDecisionEvent(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="decisions")
    action = models.CharField(max_length=32, db_index=True)
    reason = models.TextField(blank=True)
    actor_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses_invoicedecisionevent"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Решение по счёту неизменяемо.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Решение по счёту неизменяемо.")


class Payout(models.Model):
    card_id = models.IntegerField(db_index=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payouts")
    organization = models.ForeignKey(VerifiedOrganization, on_delete=models.PROTECT, related_name="payouts")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="KZT")
    status = models.CharField(max_length=32, choices=PayoutStatus.choices, default=PayoutStatus.REQUESTED)
    provider = models.CharField(max_length=32, blank=True)
    provider_payout_id = models.CharField(max_length=128, blank=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    requested_by_id = models.IntegerField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses_payout"
        ordering = ["-created_at"]


class PayoutEvent(models.Model):
    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=32, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    actor_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses_payoutevent"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Событие выплаты неизменяемо.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Событие выплаты неизменяемо.")


class ProcessedPayoutCallback(models.Model):
    event_key = models.CharField(max_length=128, unique=True)
    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name="callbacks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expenses_processedpayoutcallback"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Callback выплаты неизменяем.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Callback выплаты неизменяем.")
