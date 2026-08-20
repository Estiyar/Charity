from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OutboxEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                        serialize=False,
                    ),
                ),
                ("event_type", models.CharField(db_index=True, max_length=128)),
                ("aggregate_type", models.CharField(max_length=64)),
                ("aggregate_id", models.CharField(max_length=64)),
                ("payload", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("publish_attempts", models.PositiveIntegerField(default=0)),
            ],
            options={
                "db_table": "outbox_event",
                "ordering": ["created_at"],
            },
        ),
    ]
