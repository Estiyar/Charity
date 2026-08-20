from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("verification", "0002_protect_sensitive_identifiers"),
    ]

    operations = [
        migrations.CreateModel(
            name="EcpVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("iin_hash", models.CharField(db_index=True, max_length=64)),
                ("iin_masked", models.CharField(blank=True, max_length=32)),
                ("iin_encrypted", models.TextField(blank=True)),
                ("full_name", models.CharField(max_length=255)),
                ("birth_date", models.DateField(blank=True, null=True)),
                ("certificate_type", models.CharField(blank=True, max_length=32)),
                ("serial_number", models.CharField(blank=True, max_length=128)),
                ("issuer", models.CharField(blank=True, max_length=255)),
                ("valid_from", models.DateTimeField(blank=True, null=True)),
                ("valid_to", models.DateTimeField(blank=True, null=True)),
                ("fingerprint", models.CharField(blank=True, db_index=True, max_length=64)),
                ("cms_hash", models.CharField(blank=True, max_length=64)),
                ("adapter", models.CharField(blank=True, max_length=32)),
                ("revocation_checked", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "verification_ecp_verification",
                "ordering": ["-created_at"],
            },
        ),
    ]
