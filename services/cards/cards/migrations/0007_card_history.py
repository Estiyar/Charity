from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0006_duplicate_check"),
    ]

    operations = [
        migrations.AddField(
            model_name="fundraisingcard",
            name="diagnosis_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="clinic_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="moderation_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="CardHistoryEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(db_index=True, max_length=64)),
                ("summary", models.CharField(max_length=255)),
                ("public", models.BooleanField(default=False)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("actor_id", models.IntegerField(blank=True, null=True)),
                ("actor_role", models.CharField(blank=True, max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "card",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history_events",
                        to="cards.fundraisingcard",
                    ),
                ),
            ],
            options={
                "db_table": "cards_cardhistoryevent",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
