from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0003_beneficiary_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="CollectionReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("card_id", models.IntegerField(db_index=True)),
                ("idempotency_key", models.CharField(max_length=64, unique=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "cards_collectionreceipt"},
        ),
    ]
