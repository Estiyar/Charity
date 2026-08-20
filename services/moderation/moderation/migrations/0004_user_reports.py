from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0003_moderation_comments"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("card_id", models.IntegerField(db_index=True)),
                ("reporter_user_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("reporter_key", models.CharField(db_index=True, max_length=128)),
                ("category", models.CharField(max_length=32)),
                ("description", models.TextField()),
                ("status", models.CharField(default="pending", max_length=32)),
                ("reviewed_by", models.IntegerField(blank=True, null=True)),
                ("reviewed_by_name", models.CharField(blank=True, max_length=255)),
                ("resolution", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "moderation_user_report",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ReportAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="reports/attachments/")),
                ("file_name", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "report",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="attachments",
                        to="moderation.userreport",
                    ),
                ),
            ],
            options={
                "db_table": "moderation_report_attachment",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="userreport",
            index=models.Index(fields=["status", "created_at"], name="moderation__status__8f0b0d_idx"),
        ),
        migrations.AddIndex(
            model_name="userreport",
            index=models.Index(fields=["card_id", "reporter_key"], name="moderation__card_id__f6d0f1_idx"),
        ),
    ]
