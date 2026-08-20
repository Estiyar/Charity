from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0003_invoice_payout"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExpenseModeratorComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("comment_type", models.CharField(max_length=32)),
                ("author_id", models.IntegerField()),
                ("author_role", models.CharField(blank=True, max_length=32)),
                ("author_name", models.CharField(blank=True, max_length=255)),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("edited_at", models.DateTimeField(blank=True, null=True)),
                (
                    "expense",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="moderator_comments",
                        to="expenses.expense",
                    ),
                ),
            ],
            options={
                "db_table": "expenses_moderatorcomment",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.CreateModel(
            name="ExpenseCommentEdit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("editor_id", models.IntegerField()),
                ("editor_role", models.CharField(blank=True, max_length=32)),
                ("editor_name", models.CharField(blank=True, max_length=255)),
                ("previous_body", models.TextField()),
                ("new_body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "comment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="edits",
                        to="expenses.expensemoderatorcomment",
                    ),
                ),
            ],
            options={
                "db_table": "expenses_commentedit",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
