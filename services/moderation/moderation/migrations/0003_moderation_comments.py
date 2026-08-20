from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0002_manual_review_case"),
    ]

    operations = [
        migrations.CreateModel(
            name="ModerationComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_type", models.CharField(max_length=16)),
                ("target_id", models.IntegerField()),
                ("review_id", models.IntegerField(blank=True, null=True)),
                ("comment_type", models.CharField(max_length=32)),
                ("author_id", models.IntegerField()),
                ("author_role", models.CharField(blank=True, max_length=32)),
                ("author_name", models.CharField(blank=True, max_length=255)),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("edited_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "moderation_comment",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="moderationcomment",
            index=models.Index(fields=["target_type", "target_id"], name="moderation__target__idx"),
        ),
        migrations.CreateModel(
            name="ModerationCommentEdit",
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
                        to="moderation.moderationcomment",
                    ),
                ),
            ],
            options={
                "db_table": "moderation_commentedit",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
