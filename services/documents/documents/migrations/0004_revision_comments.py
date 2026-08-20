from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0003_document_versioning"),
    ]

    operations = [
        migrations.AlterField(
            model_name="documentversion",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("uploaded", "Загружен"),
                    ("under_review", "На проверке"),
                    ("revision_required", "На доработке"),
                    ("verified", "Проверен"),
                    ("rejected", "Отклонён"),
                    ("expired", "Истёк"),
                ],
                default="uploaded",
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="DocumentModeratorComment",
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
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="moderator_comments",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "db_table": "documents_moderatorcomment",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.CreateModel(
            name="DocumentCommentEdit",
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
                        to="documents.documentmoderatorcomment",
                    ),
                ),
            ],
            options={
                "db_table": "documents_commentedit",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
