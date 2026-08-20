from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ModerationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("card_id", models.IntegerField(db_index=True)),
                ("card_name", models.CharField(blank=True, max_length=255)),
                ("moderator_id", models.IntegerField(blank=True, null=True)),
                ("moderator_name", models.CharField(blank=True, max_length=255)),
                ("action", models.CharField(max_length=64)),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "moderation_log", "ordering": ["-created_at"]},
        ),
    ]
