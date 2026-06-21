from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_platformsettings_refund_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="balance",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
        migrations.CreateModel(
            name="BalanceTransaction",
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
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                (
                    "transaction_type",
                    models.CharField(
                        choices=[
                            ("refund_in", "Возврат на баланс"),
                            ("withdraw_out", "Вывод средств"),
                        ],
                        max_length=16,
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="balance_transactions",
                        to="users.user",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
