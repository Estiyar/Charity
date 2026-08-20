import django.db.models.deletion
import expenses.models
from django.db import migrations, models


def copy_legacy_expenses(apps, schema_editor):
    Expense = apps.get_model("expenses", "Expense")
    if not hasattr(Expense, "document_url"):
        return
    for expense in Expense.objects.all():
        if expense.document_url:
            expense.original_file = expense.document_url
            expense.file_name = getattr(expense.document_url, "name", "") or ""
        if expense.status == "pending":
            expense.status = "pending_review"
        expense.save()


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("card_id", models.IntegerField(db_index=True)),
                (
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("donation", "Пожертвование"),
                            ("expense", "Подтверждённый расход"),
                            ("payout", "Прямая выплата"),
                            ("redistribution_out", "Перераспределение исходящее"),
                            ("redistribution_in", "Перераспределение входящее"),
                            ("correction", "Корректировка"),
                        ],
                        max_length=32,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="KZT", max_length=8)),
                ("source_type", models.CharField(max_length=32)),
                ("source_id", models.CharField(max_length=64)),
                ("idempotency_key", models.CharField(max_length=128, unique=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "expenses_ledgerentry",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.CreateModel(
            name="ReconciliationReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("card_id", models.IntegerField(db_index=True)),
                ("matched", models.BooleanField(default=False)),
                ("differences", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "expenses_reconciliationreport",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="expense",
            name="category",
            field=models.CharField(
                choices=[
                    ("medicine", "Лекарства"),
                    ("treatment", "Лечение"),
                    ("clinic", "Клиника"),
                    ("transport", "Транспорт"),
                    ("living", "Проживание"),
                    ("other", "Другое"),
                ],
                default="other",
                max_length=32,
            ),
        ),
        migrations.AddField(model_name="expense", name="decision_reason", field=models.TextField(blank=True)),
        migrations.AddField(model_name="expense", name="file_name", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(
            model_name="expense",
            name="original_file",
            field=models.FileField(
                blank=True,
                null=True,
                storage=expenses.models.private_expense_storage,
                upload_to=expenses.models.original_upload_path,
            ),
        ),
        migrations.AddField(model_name="expense", name="payout_id", field=models.IntegerField(blank=True, null=True)),
        migrations.AddField(
            model_name="expense",
            name="public_file",
            field=models.FileField(blank=True, null=True, upload_to=expenses.models.public_upload_path),
        ),
        migrations.AddField(model_name="expense", name="publish_receipt", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="expense", name="reviewed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="expense", name="reviewed_by_id", field=models.IntegerField(blank=True, null=True)),
        migrations.AddField(model_name="expense", name="submitted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="expense", name="submitted_by_id", field=models.IntegerField(blank=True, null=True)),
        migrations.AlterField(
            model_name="expense",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.AlterField(
            model_name="expense",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Черновик"),
                    ("submitted", "Отправлен"),
                    ("pending_review", "На проверке"),
                    ("revision_required", "На доработке"),
                    ("approved", "Подтверждён"),
                    ("rejected", "Отклонён"),
                    ("paid", "Оплачен"),
                    ("canceled", "Отменён"),
                ],
                default="draft",
                max_length=32,
            ),
        ),
        migrations.RunPython(copy_legacy_expenses, migrations.RunPython.noop),
        migrations.RemoveField(model_name="expense", name="document_url"),
        migrations.CreateModel(
            name="ExpenseDecisionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(db_index=True, max_length=32)),
                ("reason", models.TextField(blank=True)),
                ("actor_id", models.IntegerField(blank=True, null=True)),
                ("actor_role", models.CharField(blank=True, max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "expense",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="decisions",
                        to="expenses.expense",
                    ),
                ),
            ],
            options={
                "db_table": "expenses_expensedecisionevent",
                "ordering": ["created_at", "id"],
            },
        ),
    ]



