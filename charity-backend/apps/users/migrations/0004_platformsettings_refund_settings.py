from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_user_iin"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="refund_commission_percent",
            field=models.PositiveSmallIntegerField(default=10),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="refund_deadline_days",
            field=models.PositiveSmallIntegerField(default=7),
        ),
    ]
