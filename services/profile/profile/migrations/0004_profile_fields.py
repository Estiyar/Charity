from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profile", "0003_beneficiary_representation"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="birth_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="verification_status",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="profile",
            name="ecp_status",
            field=models.CharField(default="unverified", max_length=16),
        ),
        migrations.AddField(
            model_name="profile",
            name="ecp_locked_fields",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="profile",
            name="iin_masked",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="profile",
            name="public_fields",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="profile",
            name="registered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="last_login_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
