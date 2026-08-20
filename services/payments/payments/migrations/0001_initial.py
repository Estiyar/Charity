from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Donation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("card_id", models.IntegerField(db_index=True)),
                ("card_name", models.CharField(blank=True, max_length=255)),
                ("donor_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("donor_name", models.CharField(max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("payment_status", models.CharField(default="success", max_length=16)),
                ("payment_method", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "payments_donation"},
        ),
        migrations.CreateModel(
            name="RefundDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("card_id", models.IntegerField(db_index=True)),
                ("card_snapshot", models.JSONField(default=dict)),
                ("donor_id", models.IntegerField(db_index=True)),
                ("share_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("choice", models.CharField(default="empty", max_length=16)),
                ("status", models.CharField(default="pending", max_length=16)),
                ("target_card_id", models.IntegerField(blank=True, null=True)),
                ("target_card_snapshot", models.JSONField(blank=True, default=dict)),
                ("deadline", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "donation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refund_decisions",
                        to="payments.donation",
                    ),
                ),
            ],
            options={"db_table": "payments_refunddecision", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="refunddecision",
            constraint=models.UniqueConstraint(
                fields=("donation", "card_id"),
                name="unique_refund_decision_per_donation_card",
            ),
        ),
    ]
