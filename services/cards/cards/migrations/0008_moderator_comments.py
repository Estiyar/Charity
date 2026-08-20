from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0007_card_history"),
    ]

    operations = [
        migrations.CreateModel(
            name="CardModeratorComment",
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
                    "card",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="moderator_comments",
                        to="cards.fundraisingcard",
                    ),
                ),
            ],
            options={
                "db_table": "cards_moderatorcomment",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.CreateModel(
            name="CardCommentEdit",
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
                        to="cards.cardmoderatorcomment",
                    ),
                ),
            ],
            options={
                "db_table": "cards_commentedit",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
