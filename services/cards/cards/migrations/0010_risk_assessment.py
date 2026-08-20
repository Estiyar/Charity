from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0009_suspend_reports"),
    ]

    operations = [
        migrations.CreateModel(
            name="RiskAssessment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("card_id", models.IntegerField(db_index=True)),
                ("risk_score", models.PositiveSmallIntegerField(default=0)),
                ("risk_level", models.CharField(default="low", max_length=16)),
                ("factors", models.JSONField(default=list)),
                ("config_version", models.CharField(blank=True, max_length=32)),
                ("calculated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "cards_risk_assessment",
                "ordering": ["-calculated_at"],
            },
        ),
        migrations.CreateModel(
            name="RiskOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("card_id", models.IntegerField(db_index=True)),
                ("moderator_id", models.IntegerField()),
                ("moderator_name", models.CharField(blank=True, max_length=255)),
                ("previous_score", models.PositiveSmallIntegerField(default=0)),
                ("previous_level", models.CharField(blank=True, max_length=16)),
                ("new_score", models.PositiveSmallIntegerField(default=0)),
                ("new_level", models.CharField(blank=True, max_length=16)),
                ("reason", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "cards_risk_override",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="riskassessment",
            index=models.Index(fields=["card_id", "-calculated_at"], name="cards_risk__card_id__8f01_idx"),
        ),
    ]
