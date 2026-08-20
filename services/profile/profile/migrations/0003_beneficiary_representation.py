from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("profile", "0002_protect_phone"),
    ]

    operations = [
        migrations.CreateModel(
            name="Beneficiary",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("owner_user_id", models.IntegerField(db_index=True)),
                ("full_name", models.CharField(blank=True, max_length=255)),
                ("birth_date", models.DateField(blank=True, null=True)),
                ("age", models.PositiveIntegerField(blank=True, null=True)),
                ("gender", models.CharField(blank=True, max_length=8)),
                ("city", models.CharField(blank=True, max_length=128)),
                ("clinic", models.CharField(blank=True, max_length=255)),
                ("diagnosis", models.CharField(blank=True, max_length=255)),
                ("iin_hash", models.CharField(db_index=True, max_length=64)),
                ("iin_masked", models.CharField(blank=True, max_length=32)),
                ("iin_encrypted", models.TextField(blank=True)),
                ("medical_source", models.CharField(blank=True, max_length=32)),
                ("verification_status", models.CharField(default="unverified", max_length=16)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("last_checked_at", models.DateTimeField(blank=True, null=True)),
                ("deceased", models.BooleanField(default=False)),
                ("closed", models.BooleanField(default=False)),
                ("public_fields", models.JSONField(blank=True, default=list)),
                ("review_reasons", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "profile_beneficiary",
                "ordering": ["-created_at"],
                "unique_together": {("owner_user_id", "iin_hash")},
            },
        ),
        migrations.CreateModel(
            name="Representation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("author_id", models.IntegerField(db_index=True)),
                ("relationship_type", models.CharField(max_length=32)),
                ("verification_method", models.CharField(max_length=32)),
                ("verification_status", models.CharField(default="pending", max_length=16)),
                ("document_ids", models.JSONField(blank=True, default=list)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("verified_by", models.IntegerField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "beneficiary",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="representations",
                        to="profile.beneficiary",
                    ),
                ),
            ],
            options={
                "db_table": "profile_representation",
                "ordering": ["-created_at"],
                "unique_together": {("author_id", "beneficiary")},
            },
        ),
    ]
