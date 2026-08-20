from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SensitiveAccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("actor_id", models.IntegerField(blank=True, null=True)),
                ("actor_role", models.CharField(blank=True, max_length=32)),
                ("resource_type", models.CharField(max_length=64)),
                ("resource_id", models.CharField(max_length=64)),
                ("field_name", models.CharField(max_length=64)),
                ("purpose", models.CharField(max_length=64)),
                ("request_id", models.CharField(blank=True, max_length=64)),
                ("correlation_id", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "sensitive_access_log",
                "ordering": ["-created_at"],
            },
        ),
    ]
