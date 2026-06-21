from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.common.validators import validate_iin


class Role(models.TextChoices):
    DONOR = "donor", "Донор"
    AUTHOR = "author", "Автор сбора"
    MODERATOR = "moderator", "Модератор"
    ADMIN = "admin", "Администратор"


class UserStatus(models.TextChoices):
    ACTIVE = "active", "Активен"
    BLOCKED = "blocked", "Заблокирован"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
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
    phone = models.CharField(max_length=32, blank=True)
    iin = models.CharField(max_length=12, unique=True, null=True, blank=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.DONOR)
    status = models.CharField(max_length=16, choices=UserStatus.choices, default=UserStatus.ACTIVE)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    def save(self, *args, **kwargs):
        if self.iin:
            validate_iin(self.iin)
        super().save(*args, **kwargs)

    @property
    def is_blocked(self):
        return self.status == UserStatus.BLOCKED


class BalanceTransactionType(models.TextChoices):
    REFUND_IN = "refund_in", "Возврат на баланс"
    WITHDRAW_OUT = "withdraw_out", "Вывод средств"


class BalanceTransaction(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="balance_transactions",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    transaction_type = models.CharField(
        max_length=16,
        choices=BalanceTransactionType.choices,
    )
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} {self.amount} @ user {self.user_id}"


class PlatformSettings(models.Model):
    site_name = models.CharField(max_length=255, default="е-Көмек")
    demo_payment_enabled = models.BooleanField(default=True)
    bank_integration_stub = models.BooleanField(default=True)
    escrow_integration_stub = models.BooleanField(default=True)
    pdf_auto_check_stub = models.BooleanField(default=True)
    notifications_stub = models.BooleanField(default=True)
    egov_integration_stub = models.BooleanField(default=True)
    refund_commission_percent = models.PositiveSmallIntegerField(default=10)
    refund_deadline_days = models.PositiveSmallIntegerField(default=7)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Platform settings"

    @classmethod
    def get_solo(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
