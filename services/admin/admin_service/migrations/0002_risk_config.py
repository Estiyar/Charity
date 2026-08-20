from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("admin_service", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="RiskConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.CharField(default="1.0", max_length=32)),
                ("factor_weights", models.JSONField(default=dict)),
                ("risk_thresholds", models.JSONField(default=dict)),
                ("business_limits", models.JSONField(default=dict)),
                ("active", models.BooleanField(default=True)),
                ("created_by", models.IntegerField(blank=True, null=True)),
                ("created_by_name", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "admin_risk_config", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="RiskConfigAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_id", models.IntegerField(blank=True, null=True)),
                ("actor_name", models.CharField(blank=True, max_length=255)),
                ("action", models.CharField(max_length=64)),
                ("previous_snapshot", models.JSONField(default=dict)),
                ("new_snapshot", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "config",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_entries",
                        to="admin_service.riskconfig",
                    ),
                ),
            ],
            options={"db_table": "admin_risk_config_audit", "ordering": ["-created_at"]},
        ),
    ]
