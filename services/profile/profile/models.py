from django.db import models

from ekomek_common.crypto import decrypt_value, protect_identifier, protect_phone


class Profile(models.Model):
    user_id = models.IntegerField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=16, blank=True)
    bio = models.TextField(blank=True)
    city = models.CharField(max_length=128, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    phone_encrypted = models.TextField(blank=True)
    phone_masked = models.CharField(max_length=32, blank=True)
    avatar = models.ImageField(upload_to="profiles/", null=True, blank=True)
    verification_status = models.CharField(max_length=16, blank=True)
    ecp_status = models.CharField(max_length=16, default="unverified")
    ecp_locked_fields = models.JSONField(default=list, blank=True)
    iin_masked = models.CharField(max_length=32, blank=True)
    public_fields = models.JSONField(default=list, blank=True)
    is_public_phone = models.BooleanField(default=False)
    is_public_email = models.BooleanField(default=False)
    registered_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profile_profile"

    def assign_phone(self, raw_phone):
        protected = protect_phone(raw_phone)
        self.phone_encrypted = protected["encrypted"]
        self.phone_masked = protected["masked"]

    def decrypted_phone(self):
        return decrypt_value(self.phone_encrypted)


class Beneficiary(models.Model):
    owner_user_id = models.IntegerField(db_index=True)
    full_name = models.CharField(max_length=255, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=8, blank=True)
    city = models.CharField(max_length=128, blank=True)
    clinic = models.CharField(max_length=255, blank=True)
    diagnosis = models.CharField(max_length=255, blank=True)
    iin_hash = models.CharField(max_length=64, db_index=True)
    iin_masked = models.CharField(max_length=32, blank=True)
    iin_encrypted = models.TextField(blank=True)
    medical_source = models.CharField(max_length=32, blank=True)
    medical_record_hash = models.CharField(max_length=64, blank=True, db_index=True)
    verification_status = models.CharField(max_length=16, default="unverified")
    verified_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    deceased = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)
    public_fields = models.JSONField(default=list, blank=True)
    review_reasons = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profile_beneficiary"
        unique_together = ("owner_user_id", "iin_hash")
        ordering = ["-created_at"]

    def assign_iin(self, raw_iin):
        protected = protect_identifier(raw_iin)
        self.iin_hash = protected["hash"]
        self.iin_masked = protected["masked"]
        self.iin_encrypted = protected["encrypted"]


class Representation(models.Model):
    author_id = models.IntegerField(db_index=True)
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name="representations")
    relationship_type = models.CharField(max_length=32)
    verification_method = models.CharField(max_length=32)
    verification_status = models.CharField(max_length=16, default="pending")
    document_ids = models.JSONField(default=list, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "profile_representation"
        unique_together = ("author_id", "beneficiary")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["verification_status"], name="profile_rep_verif_idx"),
        ]
