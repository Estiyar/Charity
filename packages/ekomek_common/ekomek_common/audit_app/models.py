from django.db import models


class SensitiveAccessLog(models.Model):
    actor_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    resource_type = models.CharField(max_length=64)
    resource_id = models.CharField(max_length=64)
    field_name = models.CharField(max_length=64)
    purpose = models.CharField(max_length=64)
    request_id = models.CharField(max_length=64, blank=True)
    correlation_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sensitive_access_log"
        ordering = ["-created_at"]
