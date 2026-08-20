from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="MedicalRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("iin", models.CharField(max_length=12, unique=True)),
                ("full_name", models.CharField(max_length=255)),
                ("birth_date", models.DateField()),
                ("gender", models.CharField(max_length=8)),
                ("city", models.CharField(max_length=128)),
                ("clinic", models.CharField(max_length=255)),
            ],
            options={"db_table": "verification_medical_record", "ordering": ["full_name"]},
        ),
        migrations.CreateModel(
            name="MedicalDiagnosis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("stage", models.CharField(blank=True, max_length=64)),
                ("diagnosed_date", models.DateField()),
                (
                    "record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="diagnoses",
                        to="verification.medicalrecord",
                    ),
                ),
            ],
            options={"db_table": "verification_medical_diagnosis", "ordering": ["-diagnosed_date"]},
        ),
        migrations.CreateModel(
            name="FraudProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("iin", models.CharField(max_length=12, unique=True)),
                ("full_name", models.CharField(max_length=255)),
                ("risk_score", models.PositiveSmallIntegerField()),
                ("risk_level", models.CharField(max_length=8)),
                ("reasons", models.JSONField(default=list)),
            ],
            options={"db_table": "verification_fraud_profile", "ordering": ["-risk_score"]},
        ),
    ]
