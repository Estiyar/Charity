from django.db import models

from ekomek_common.crypto import protect_identifier


class Gender(models.TextChoices):
    MALE = "male", "Мужской"
    FEMALE = "female", "Женский"


class RiskLevel(models.TextChoices):
    LOW = "low", "Низкий"
    MEDIUM = "medium", "Средний"
    HIGH = "high", "Высокий"


class HashedIinMixin:
    def assign_iin(self, raw_iin):
        protected = protect_identifier(raw_iin)
        self.iin_hash = protected["hash"]
        self.iin_masked = protected["masked"]


class MedicalRecord(HashedIinMixin, models.Model):
    iin_hash = models.CharField(max_length=64, unique=True)
    iin_masked = models.CharField(max_length=32, blank=True)
    full_name = models.CharField(max_length=255)
    birth_date = models.DateField()
    gender = models.CharField(max_length=8, choices=Gender.choices)
    city = models.CharField(max_length=128)
    clinic = models.CharField(max_length=255)

    class Meta:
        db_table = "verification_medical_record"
        ordering = ["full_name"]


class MedicalDiagnosis(models.Model):
    record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name="diagnoses")
    name = models.CharField(max_length=255)
    stage = models.CharField(max_length=64, blank=True)
    diagnosed_date = models.DateField()

    class Meta:
        db_table = "verification_medical_diagnosis"
        ordering = ["-diagnosed_date"]


class FraudProfile(HashedIinMixin, models.Model):
    iin_hash = models.CharField(max_length=64, unique=True)
    iin_masked = models.CharField(max_length=32, blank=True)
    full_name = models.CharField(max_length=255)
    risk_score = models.PositiveSmallIntegerField()
    risk_level = models.CharField(max_length=8, choices=RiskLevel.choices)
    reasons = models.JSONField(default=list)

    class Meta:
        db_table = "verification_fraud_profile"
        ordering = ["-risk_score"]


class EcpVerification(models.Model):
    iin_hash = models.CharField(max_length=64, db_index=True)
    iin_masked = models.CharField(max_length=32, blank=True)
    iin_encrypted = models.TextField(blank=True)
    full_name = models.CharField(max_length=255)
    birth_date = models.DateField(null=True, blank=True)
    certificate_type = models.CharField(max_length=32, blank=True)
    serial_number = models.CharField(max_length=128, blank=True)
    issuer = models.CharField(max_length=255, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    cms_hash = models.CharField(max_length=64, blank=True)
    adapter = models.CharField(max_length=32, blank=True)
    revocation_checked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "verification_ecp_verification"
        ordering = ["-created_at"]

    def assign_iin(self, raw_iin):
        protected = protect_identifier(raw_iin)
        self.iin_hash = protected["hash"]
        self.iin_masked = protected["masked"]
        self.iin_encrypted = protected["encrypted"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("ECP verification records cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("ECP verification records cannot be deleted.")
