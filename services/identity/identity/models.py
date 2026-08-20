from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from ekomek_common.constants import Role, UserStatus
from ekomek_common.crypto import decrypt_value, protect_identifier, protect_phone
from ekomek_common.validators import validate_iin


class RoleChoices(models.TextChoices):
    DONOR = Role.DONOR, "Донор"
    AUTHOR = Role.AUTHOR, "Автор сбора"
    MODERATOR = Role.MODERATOR, "Модератор"
    ADMIN = Role.ADMIN, "Администратор"


class UserStatusChoices(models.TextChoices):
    ACTIVE = UserStatus.ACTIVE, "Активен"
    UNVERIFIED = UserStatus.UNVERIFIED, "Не подтверждён"
    ECP_VERIFIED = UserStatus.ECP_VERIFIED, "Подтверждён ЭЦП"
    MANUAL_REVIEW = UserStatus.MANUAL_REVIEW, "Ручная проверка"
    REJECTED = UserStatus.REJECTED, "Отклонён"
    BLOCKED = UserStatus.BLOCKED, "Заблокирован"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        raw_iin = extra.pop("iin", None)
        raw_phone = extra.pop("phone", "")
        user = self.model(email=email, **extra)
        if raw_phone:
            user.assign_phone(raw_phone)
        if raw_iin:
            user.assign_iin(raw_iin)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_encrypted = models.TextField(blank=True)
    phone_masked = models.CharField(max_length=32, blank=True)
    iin_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    iin_masked = models.CharField(max_length=32, blank=True)
    iin_encrypted = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    ecp_verification_id = models.IntegerField(null=True, blank=True)
    ecp_locked_fields = models.JSONField(default=list, blank=True)
    certificate_type = models.CharField(max_length=32, blank=True)
    certificate_serial = models.CharField(max_length=128, blank=True)
    certificate_issuer = models.CharField(max_length=255, blank=True)
    certificate_valid_to = models.DateTimeField(null=True, blank=True)
    role = models.CharField(max_length=16, choices=RoleChoices.choices, default=Role.DONOR)
    status = models.CharField(
        max_length=16, choices=UserStatusChoices.choices, default=UserStatus.ACTIVE
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "identity_user"

    def assign_iin(self, raw_iin):
        validate_iin(raw_iin)
        protected = protect_identifier(raw_iin)
        self.iin_hash = protected["hash"]
        self.iin_masked = protected["masked"]
        self.iin_encrypted = protected["encrypted"]

    def assign_phone(self, raw_phone):
        protected = protect_phone(raw_phone)
        self.phone_encrypted = protected["encrypted"]
        self.phone_masked = protected["masked"]

    def decrypted_phone(self):
        return decrypt_value(self.phone_encrypted)

    @property
    def is_blocked(self):
        return self.status == UserStatus.BLOCKED

    @property
    def can_login(self):
        return self.status in UserStatus.CAN_LOGIN

    @property
    def can_create_public_fundraiser(self):
        return self.role == Role.AUTHOR and self.status in UserStatus.CAN_CREATE_FUNDRAISER

    def apply_ecp_profile(self, payload, verification_id):
        self.full_name = payload["full_name"]
        self.birth_date = payload.get("birth_date")
        self.ecp_verification_id = verification_id
        self.ecp_locked_fields = ["full_name", "iin", "birth_date"]
        self.certificate_type = payload.get("certificate_type") or ""
        self.certificate_serial = payload.get("serial_number") or ""
        self.certificate_issuer = payload.get("issuer") or ""
        self.certificate_valid_to = payload.get("valid_to")
        if payload.get("iin"):
            self.assign_iin(payload["iin"])


class BalanceTransactionType(models.TextChoices):
    REFUND_IN = "refund_in", "Возврат на баланс"
    WITHDRAW_OUT = "withdraw_out", "Вывод средств"


class BalanceTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="balance_transactions")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    transaction_type = models.CharField(max_length=16, choices=BalanceTransactionType.choices)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "identity_balance_transaction"
        ordering = ["-created_at"]
