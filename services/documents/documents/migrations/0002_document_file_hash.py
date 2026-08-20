from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="file_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
    ]
