from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0005_catalog_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="fundraisingcard",
            name="payout_details_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="request_fingerprint_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="duplicate_suspected",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="duplicate_override",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="duplicate_signals",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="duplicate_matches",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="duplicate_fingerprint",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="duplicate_risk_delta",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="duplicate_checked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="DuplicateCheck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fingerprint", models.CharField(max_length=64)),
                ("suspected", models.BooleanField(default=False)),
                ("signals", models.JSONField(blank=True, default=list)),
                ("matches", models.JSONField(blank=True, default=list)),
                ("risk_delta", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "card",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="duplicate_checks",
                        to="cards.fundraisingcard",
                    ),
                ),
            ],
            options={
                "db_table": "cards_duplicatecheck",
                "unique_together": {("card", "fingerprint")},
            },
        ),
    ]
