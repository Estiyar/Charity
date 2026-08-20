from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ManualReviewCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("subject_type", models.CharField(max_length=16)),
                ("subject_id", models.IntegerField()),
                ("subject_label", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(default="open", max_length=32)),
                ("risk_score", models.PositiveSmallIntegerField(default=0)),
                ("risk_level", models.CharField(blank=True, max_length=32)),
                ("risk_reasons", models.JSONField(blank=True, default=list)),
                ("verification_snapshot", models.JSONField(blank=True, default=dict)),
                ("duplicate_signals", models.JSONField(blank=True, default=list)),
                ("document_metadata", models.JSONField(blank=True, default=list)),
                ("evidence_snapshot", models.JSONField(blank=True, default=dict)),
                ("previous_subject_status", models.CharField(blank=True, max_length=64)),
                ("opened_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "moderation_manual_review_case",
                "ordering": ["-opened_at"],
            },
        ),
        migrations.CreateModel(
            name="ReviewDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=32)),
                ("moderator_id", models.IntegerField()),
                ("moderator_name", models.CharField(blank=True, max_length=255)),
                ("comment", models.TextField(blank=True)),
                ("evidence_reviewed", models.JSONField(blank=True, default=list)),
                ("idempotency_key", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "case",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="decisions",
                        to="moderation.manualreviewcase",
                    ),
                ),
            ],
            options={
                "db_table": "moderation_review_decision",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="manualreviewcase",
            index=models.Index(fields=["status", "subject_type"], name="moderation__status_7f1a2c_idx"),
        ),
        migrations.AddIndex(
            model_name="manualreviewcase",
            index=models.Index(
                fields=["subject_type", "subject_id"],
                name="moderation__subject_3c91ab_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="manualreviewcase",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="open"),
                fields=("subject_type", "subject_id"),
                name="one_open_manual_review_case",
            ),
        ),
        migrations.AddConstraint(
            model_name="reviewdecision",
            constraint=models.UniqueConstraint(
                fields=("case", "idempotency_key"),
                name="unique_review_decision_key",
            ),
        ),
    ]
