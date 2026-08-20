from django.db import migrations, models
import uuid


def fill_idempotency_keys(apps, schema_editor):
    Donation = apps.get_model("payments", "Donation")
    for donation in Donation.objects.filter(idempotency_key=""):
        donation.idempotency_key = f"legacy-{donation.id}-{uuid.uuid4().hex}"
        donation.save(update_fields=["idempotency_key"])


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="donation",
            name="payment_status",
            field=models.CharField(default="pending", max_length=24),
        ),
        migrations.AddField(
            model_name="donation",
            name="currency",
            field=models.CharField(default="KZT", max_length=8),
        ),
        migrations.AddField(
            model_name="donation",
            name="email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="donation",
            name="phone",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="donation",
            name="provider",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="donation",
            name="provider_payment_id",
            field=models.CharField(blank=True, max_length=128, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="donation",
            name="idempotency_key",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.RunPython(fill_idempotency_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="donation",
            name="idempotency_key",
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AddField(
            model_name="donation",
            name="redirect_url",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="donation",
            name="failed_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="donation",
            name="collected_applied",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="donation",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="donation",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.CreateModel(
            name="PaymentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("event_type", models.CharField(max_length=32)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "donation",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="events",
                        to="payments.donation",
                    ),
                ),
            ],
            options={"db_table": "payments_paymentevent", "ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="LedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("card_id", models.IntegerField(db_index=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="KZT", max_length=8)),
                ("entry_type", models.CharField(max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "donation",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="ledger_entries",
                        to="payments.donation",
                    ),
                ),
            ],
            options={"db_table": "payments_ledgerentry"},
        ),
        migrations.AddConstraint(
            model_name="ledgerentry",
            constraint=models.UniqueConstraint(
                fields=("donation", "entry_type"),
                name="unique_ledger_entry_per_donation_type",
            ),
        ),
        migrations.CreateModel(
            name="ProcessedProviderEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("provider", models.CharField(max_length=32)),
                ("event_key", models.CharField(max_length=160)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("processed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "payments_processedproviderevent"},
        ),
        migrations.AddConstraint(
            model_name="processedproviderevent",
            constraint=models.UniqueConstraint(
                fields=("provider", "event_key"),
                name="unique_processed_provider_event",
            ),
        ),
    ]
