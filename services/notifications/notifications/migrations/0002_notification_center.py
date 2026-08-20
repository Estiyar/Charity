from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="notification",
            old_name="user_id",
            new_name="recipient_id",
        ),
        migrations.AddField(
            model_name="notification",
            name="deep_link",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="notification",
            name="idempotency_key",
            field=models.CharField(blank=True, default="", max_length=255, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(blank=True, db_index=True, default="", max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="notification",
            name="payload",
            field=models.JSONField(default=dict),
        ),
        migrations.CreateModel(
            name="NotificationDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel", models.CharField(choices=[("email", "Email"), ("sms", "SMS"), ("push", "Push")], max_length=16)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("retrying", "Retrying"), ("sent", "Sent"), ("failed", "Failed"), ("skipped", "Skipped")], db_index=True, default="pending", max_length=16)),
                ("destination", models.CharField(blank=True, max_length=255)),
                ("provider", models.CharField(blank=True, max_length=64)),
                ("provider_message_id", models.CharField(blank=True, max_length=128)),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("next_attempt_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("notification", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deliveries", to="notifications.notification")),
            ],
            options={
                "db_table": "notifications_delivery",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.CreateModel(
            name="NotificationDeliveryLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempt_number", models.PositiveSmallIntegerField()),
                ("status", models.CharField(choices=[("pending", "Pending"), ("retrying", "Retrying"), ("sent", "Sent"), ("failed", "Failed"), ("skipped", "Skipped")], max_length=16)),
                ("response_payload", models.JSONField(default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("delivery", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="logs", to="notifications.notificationdelivery")),
            ],
            options={
                "db_table": "notifications_delivery_log",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="notificationdelivery",
            constraint=models.UniqueConstraint(fields=("notification", "channel"), name="notifications_delivery_channel_unique"),
        ),
    ]
