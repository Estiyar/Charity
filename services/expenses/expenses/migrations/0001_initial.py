from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("card_id", models.IntegerField(db_index=True)),
                ("card_name", models.CharField(blank=True, max_length=255)),
                ("date", models.DateField()),
                ("purpose", models.CharField(max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("comment", models.TextField(blank=True)),
                ("document_url", models.FileField(blank=True, null=True, upload_to="cards/expenses/")),
                ("status", models.CharField(default="pending", max_length=16)),
                ("moderator_comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "expenses_expense", "ordering": ["-created_at"]},
        ),
    ]
