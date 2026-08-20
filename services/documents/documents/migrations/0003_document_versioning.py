import django.db.models.deletion
import documents.models
from django.db import migrations, models


def copy_legacy_documents(apps, schema_editor):
    Document = apps.get_model("documents", "Document")
    DocumentVersion = apps.get_model("documents", "DocumentVersion")
    if not hasattr(Document, "file_url"):
        return
    for document in Document.objects.all():
        version = DocumentVersion.objects.create(
            document=document,
            version_number=1,
            verification_status=document.status or "uploaded",
            file_hash=document.file_hash or "",
            original_file=document.file_url,
            file_name=document.file_name or "",
            file_type=document.file_type or "",
            has_confidential=document.has_confidential,
            moderator_comment=document.moderator_comment or "",
            visibility=document.visibility,
        )
        document.current_version = version
        document.save(update_fields=["current_version"])


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0002_document_file_hash"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="document_type",
            field=models.CharField(
                choices=[
                    ("medical", "Медицинский"),
                    ("diagnosis", "Диагноз"),
                    ("clinic", "Клиника"),
                    ("identity", "Удостоверение"),
                    ("representation", "Представительство"),
                    ("other", "Другое"),
                ],
                default="medical",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="visibility",
            field=models.CharField(
                choices=[
                    ("staff", "Сотрудники"),
                    ("author", "Автор"),
                    ("public", "Публичный"),
                ],
                default="public",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="document",
            name="id",
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
        ),
        migrations.CreateModel(
            name="DocumentVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version_number", models.PositiveIntegerField()),
                ("issued_at", models.DateField(blank=True, null=True)),
                ("issuer", models.CharField(blank=True, max_length=255)),
                (
                    "verification_status",
                    models.CharField(
                        choices=[
                            ("uploaded", "Загружен"),
                            ("under_review", "На проверке"),
                            ("verified", "Проверен"),
                            ("rejected", "Отклонён"),
                            ("expired", "Истёк"),
                        ],
                        default="uploaded",
                        max_length=16,
                    ),
                ),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("verified_by_id", models.IntegerField(blank=True, null=True)),
                ("expires_at", models.DateField(blank=True, null=True)),
                ("file_hash", models.CharField(db_index=True, max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "visibility",
                    models.CharField(
                        choices=[
                            ("staff", "Сотрудники"),
                            ("author", "Автор"),
                            ("public", "Публичный"),
                        ],
                        default="public",
                        max_length=16,
                    ),
                ),
                (
                    "original_file",
                    models.FileField(
                        storage=documents.models.private_document_storage,
                        upload_to=documents.models.original_upload_path,
                    ),
                ),
                ("public_file", models.FileField(blank=True, upload_to=documents.models.public_upload_path)),
                ("file_name", models.CharField(max_length=255)),
                ("file_type", models.CharField(max_length=32)),
                ("has_confidential", models.BooleanField(default=True)),
                ("moderator_comment", models.TextField(blank=True)),
                ("uploaded_by_id", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="documents.document",
                    ),
                ),
                (
                    "supersedes",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="superseded_by",
                        to="documents.documentversion",
                    ),
                ),
            ],
            options={
                "db_table": "documents_documentversion",
                "ordering": ["version_number", "id"],
                "unique_together": {("document", "version_number")},
            },
        ),
        migrations.CreateModel(
            name="DocumentAuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(db_index=True, max_length=64)),
                ("summary", models.CharField(max_length=255)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("actor_id", models.IntegerField(blank=True, null=True)),
                ("actor_role", models.CharField(blank=True, max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_events",
                        to="documents.document",
                    ),
                ),
                (
                    "version",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_events",
                        to="documents.documentversion",
                    ),
                ),
            ],
            options={
                "db_table": "documents_documentauditevent",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddField(
            model_name="document",
            name="current_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="documents.documentversion",
            ),
        ),
        migrations.RunPython(copy_legacy_documents, migrations.RunPython.noop),
        migrations.RemoveField(model_name="document", name="file_hash"),
        migrations.RemoveField(model_name="document", name="file_name"),
        migrations.RemoveField(model_name="document", name="file_type"),
        migrations.RemoveField(model_name="document", name="file_url"),
        migrations.RemoveField(model_name="document", name="has_confidential"),
        migrations.RemoveField(model_name="document", name="moderator_comment"),
        migrations.RemoveField(model_name="document", name="status"),
    ]
