from decimal import Decimal

from django.db import models

from ekomek_common.constants import PUBLIC_CARD_STATUSES, VIEWABLE_PUBLIC_STATUSES, CardStatus
from ekomek_common.crypto import protect_document_number, protect_identifier, protect_phone


class Gender(models.TextChoices):
    MALE = "male", "Мужской"
    FEMALE = "female", "Женский"


class FundraisingCard(models.Model):
    author_id = models.IntegerField(db_index=True)
    author_email = models.EmailField(blank=True)
    author_full_name = models.CharField(max_length=255, blank=True)

    full_name = models.CharField(max_length=255, blank=True)
    diagnosis = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    clinic = models.CharField(max_length=255, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=8, choices=Gender.choices, blank=True)
    description = models.TextField(blank=True)
    photo_url = models.ImageField(upload_to="cards/photos/", null=True, blank=True)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    collected_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    end_date = models.DateField()
    status = models.CharField(max_length=32, choices=[(item, item) for item in CardStatus.ALL], default=CardStatus.DRAFT)
    iin_hash = models.CharField(max_length=64, blank=True, db_index=True)
    iin_masked = models.CharField(max_length=32, blank=True)
    iin_encrypted = models.TextField(blank=True)
    document_number_hash = models.CharField(max_length=64, blank=True, db_index=True)
    document_number_encrypted = models.TextField(blank=True)
    document_number_masked = models.CharField(max_length=32, blank=True)
    contact_phone_encrypted = models.TextField(blank=True)
    contact_phone_masked = models.CharField(max_length=32, blank=True)
    contact_email = models.EmailField(blank=True)
    moderator_comment = models.TextField(blank=True)
    is_self = models.BooleanField(default=False)
    beneficiary_id = models.IntegerField(null=True, blank=True, db_index=True)
    representation_id = models.IntegerField(null=True, blank=True, db_index=True)
    relationship_type = models.CharField(max_length=32, blank=True)
    high_risk = models.BooleanField(default=False)
    review_reasons = models.JSONField(default=list, blank=True)
    suspend_reason = models.TextField(blank=True)
    status_before_suspend = models.CharField(max_length=32, blank=True)
    report_risk_score = models.PositiveSmallIntegerField(default=0)
    unique_report_count = models.PositiveIntegerField(default=0)
    medical_source = models.CharField(max_length=32, blank=True)
    needs_extra_review = models.BooleanField(default=False)
    payout_details_hash = models.CharField(max_length=64, blank=True, db_index=True)
    request_fingerprint_hash = models.CharField(max_length=64, blank=True, db_index=True)
    duplicate_suspected = models.BooleanField(default=False)
    duplicate_override = models.BooleanField(default=False)
    duplicate_signals = models.JSONField(default=list, blank=True)
    duplicate_matches = models.JSONField(default=list, blank=True)
    duplicate_fingerprint = models.CharField(max_length=64, blank=True)
    duplicate_risk_delta = models.PositiveIntegerField(default=0)
    duplicate_checked_at = models.DateTimeField(null=True, blank=True)
    diagnosis_verified_at = models.DateTimeField(null=True, blank=True)
    clinic_verified_at = models.DateTimeField(null=True, blank=True)
    moderation_verified_at = models.DateTimeField(null=True, blank=True)
    escrow_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    escrow_pending = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cards_fundraisingcard"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="cards_status_idx"),
            models.Index(fields=["city"], name="cards_city_idx"),
            models.Index(fields=["diagnosis"], name="cards_diagnosis_idx"),
            models.Index(fields=["age"], name="cards_age_idx"),
            models.Index(fields=["target_amount"], name="cards_target_amount_idx"),
            models.Index(fields=["collected_amount"], name="cards_collected_idx"),
            models.Index(fields=["end_date"], name="cards_end_date_idx"),
            models.Index(fields=["status", "end_date"], name="cards_status_end_idx"),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from .catalog_cache import invalidate_catalog_cache

        invalidate_catalog_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        from .catalog_cache import invalidate_catalog_cache

        invalidate_catalog_cache()

    def assign_iin(self, raw_iin):
        protected = protect_identifier(raw_iin)
        self.iin_hash = protected["hash"]
        self.iin_masked = protected["masked"]
        self.iin_encrypted = protected["encrypted"]

    def assign_document_number(self, raw_number):
        protected = protect_document_number(raw_number)
        self.document_number_hash = protected["hash"]
        self.document_number_masked = protected["masked"]
        self.document_number_encrypted = protected["encrypted"]

    def assign_contact_phone(self, raw_phone):
        protected = protect_phone(raw_phone)
        self.contact_phone_encrypted = protected["encrypted"]
        self.contact_phone_masked = protected["masked"]

    @property
    def is_public(self):
        return self.status in PUBLIC_CARD_STATUSES

    @property
    def is_publicly_viewable(self):
        return self.status in VIEWABLE_PUBLIC_STATUSES

    @property
    def masked_phone(self):
        return self.contact_phone_masked

    @property
    def progress_percent(self):
        if not self.target_amount:
            return Decimal("0.0")
        percent = (self.collected_amount / self.target_amount) * Decimal("100")
        if percent > Decimal("100"):
            percent = Decimal("100")
        return percent.quantize(Decimal("0.1"))

    @property
    def escrow_received(self):
        return self.collected_amount

    @property
    def escrow_available(self):
        return float(self.escrow_received) - float(self.escrow_spent) - float(self.escrow_pending)

    @property
    def escrow_balance(self):
        return float(self.escrow_received) - float(self.escrow_spent)


class DuplicateCheck(models.Model):
    card = models.ForeignKey(
        FundraisingCard,
        on_delete=models.CASCADE,
        related_name="duplicate_checks",
    )
    fingerprint = models.CharField(max_length=64)
    suspected = models.BooleanField(default=False)
    signals = models.JSONField(default=list, blank=True)
    matches = models.JSONField(default=list, blank=True)
    risk_delta = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cards_duplicatecheck"
        unique_together = ("card", "fingerprint")


class CardHistoryEvent(models.Model):
    card = models.ForeignKey(
        FundraisingCard,
        on_delete=models.CASCADE,
        related_name="history_events",
    )
    event_type = models.CharField(max_length=64, db_index=True)
    summary = models.CharField(max_length=255)
    public = models.BooleanField(default=False)
    payload = models.JSONField(default=dict, blank=True)
    actor_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cards_cardhistoryevent"
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("История карточки неизменяема.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("История карточки неизменяема.")


class CollectionReceipt(models.Model):
    card_id = models.IntegerField(db_index=True)
    idempotency_key = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cards_collectionreceipt"


from .comment_models import CardCommentEdit, CardModeratorComment  # noqa: E402,F401

