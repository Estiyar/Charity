from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("card_id", models.IntegerField(db_index=True)),
                ("file_url", models.FileField(upload_to="cards/documents/")),
                ("file_name", models.CharField(max_length=255)),
                ("file_type", models.CharField(max_length=32)),
                ("status", models.CharField(default="uploaded", max_length=16)),
                ("has_confidential", models.BooleanField(default=False)),
                ("moderator_comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "documents_document", "ordering": ["-created_at"]},
        ),
    ]
