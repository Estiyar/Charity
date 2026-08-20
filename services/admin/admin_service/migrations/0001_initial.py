from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="City",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=128, unique=True)),
            ],
            options={"db_table": "admin_city"},
        ),
        migrations.CreateModel(
            name="Diagnosis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255, unique=True)),
            ],
            options={"db_table": "admin_diagnosis"},
        ),
        migrations.CreateModel(
            name="PlatformSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("site_name", models.CharField(default="е-Көмек", max_length=255)),
                ("demo_payment_enabled", models.BooleanField(default=True)),
                ("bank_integration_stub", models.BooleanField(default=True)),
                ("escrow_integration_stub", models.BooleanField(default=True)),
                ("pdf_auto_check_stub", models.BooleanField(default=True)),
                ("notifications_stub", models.BooleanField(default=True)),
                ("egov_integration_stub", models.BooleanField(default=True)),
                ("refund_commission_percent", models.PositiveSmallIntegerField(default=10)),
                ("refund_deadline_days", models.PositiveSmallIntegerField(default=7)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "admin_platformsettings"},
        ),
        migrations.CreateModel(
            name="AdminAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("actor_id", models.IntegerField(blank=True, null=True)),
                ("action", models.CharField(max_length=128)),
                ("payload", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "admin_audit_event", "ordering": ["-created_at"]},
        ),
    ]
