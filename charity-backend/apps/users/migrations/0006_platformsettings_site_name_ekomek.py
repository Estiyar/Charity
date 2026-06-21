from django.db import migrations, models


def rename_site(apps, schema_editor):
    PlatformSettings = apps.get_model("users", "PlatformSettings")
    PlatformSettings.objects.filter(site_name="Charity Platform").update(site_name="е-Көмек")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_user_balance_balancetransaction"),
    ]

    operations = [
        migrations.AlterField(
            model_name="platformsettings",
            name="site_name",
            field=models.CharField(default="е-Көмек", max_length=255),
        ),
        migrations.RunPython(rename_site, migrations.RunPython.noop),
    ]
