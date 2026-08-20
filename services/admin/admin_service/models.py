from django.db import models
from django.utils import timezone

from ekomek_common.risk import (
    DEFAULT_BUSINESS_LIMITS,
    DEFAULT_RISK_FACTOR_WEIGHTS,
    DEFAULT_RISK_THRESHOLDS,
    RISK_CONFIG_VERSION,
)


class City(models.Model):
    name = models.CharField(max_length=128, unique=True)

    class Meta:
        db_table = "admin_city"


class Diagnosis(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = "admin_diagnosis"


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
        db_table = "admin_platformsettings"
        verbose_name_plural = "Platform settings"

    @classmethod
    def get_solo(cls):
        settings, _created = cls.objects.get_or_create(pk=1)
        return settings


class RiskConfig(models.Model):
    version = models.CharField(max_length=32, default=RISK_CONFIG_VERSION)
    factor_weights = models.JSONField(default=dict)
    risk_thresholds = models.JSONField(default=dict)
    business_limits = models.JSONField(default=dict)
    active = models.BooleanField(default=True)
    created_by = models.IntegerField(null=True, blank=True)
    created_by_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_risk_config"
        ordering = ["-created_at"]

    @classmethod
    def get_active(cls):
        config = cls.objects.filter(active=True).order_by("-created_at").first()
        if config is None:
            config = cls.objects.create(
                factor_weights=dict(DEFAULT_RISK_FACTOR_WEIGHTS),
                risk_thresholds=dict(DEFAULT_RISK_THRESHOLDS),
                business_limits=dict(DEFAULT_BUSINESS_LIMITS),
            )
        return config

    def get_weights(self):
        merged = dict(DEFAULT_RISK_FACTOR_WEIGHTS)
        merged.update(self.factor_weights or {})
        return merged

    def get_thresholds(self):
        merged = dict(DEFAULT_RISK_THRESHOLDS)
        merged.update(self.risk_thresholds or {})
        return merged

    def get_limits(self):
        merged = dict(DEFAULT_BUSINESS_LIMITS)
        merged.update(self.business_limits or {})
        return merged


class RiskConfigAudit(models.Model):
    config = models.ForeignKey(RiskConfig, on_delete=models.CASCADE, related_name="audit_entries")
    actor_id = models.IntegerField(null=True, blank=True)
    actor_name = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=64)
    previous_snapshot = models.JSONField(default=dict)
    new_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_risk_config_audit"
        ordering = ["-created_at"]


class AdminAuditEvent(models.Model):
    actor_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_audit_event"
        ordering = ["-created_at"]
