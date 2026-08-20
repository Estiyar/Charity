from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("user_id", models.IntegerField(db_index=True)),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("event_type", models.CharField(blank=True, max_length=128)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "notifications_notification", "ordering": ["-created_at"]},
        ),
    ]
