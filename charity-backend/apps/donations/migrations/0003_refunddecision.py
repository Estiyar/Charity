import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0004_fundraisingcard_recipient_iin_is_self"),
        ("donations", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RefundDecision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("share_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                (
                    "choice",
                    models.CharField(
                        choices=[
                            ("empty", "Не выбрано"),
                            ("keep", "Оставить семье"),
                            ("refund", "Возврат"),
                            ("redirect", "Перенаправить"),
                        ],
                        default="empty",
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ожидает решения"),
                            ("done", "Выполнено"),
                            ("expired", "Истёк срок"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("deadline", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "card",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refund_decisions",
                        to="cards.fundraisingcard",
                    ),
                ),
                (
                    "donation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refund_decisions",
                        to="donations.donation",
                    ),
                ),
                (
                    "donor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refund_decisions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "target_card",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="incoming_refund_decisions",
                        to="cards.fundraisingcard",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="refunddecision",
            constraint=models.UniqueConstraint(
                fields=("donation", "card"),
                name="unique_refund_decision_per_donation_card",
            ),
        ),
    ]
