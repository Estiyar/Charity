from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0002_protect_sensitive_identifiers"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fundraisingcard",
            name="full_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="fundraisingcard",
            name="diagnosis",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="fundraisingcard",
            name="city",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="beneficiary_id",
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="representation_id",
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="relationship_type",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="high_risk",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="review_reasons",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="medical_source",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
