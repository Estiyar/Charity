import re

from django.db import migrations, models


def protect_existing_users(apps, schema_editor):
    from ekomek_common.crypto import protect_identifier, protect_phone

    User = apps.get_model("identity", "User")
    for user in User.objects.all():
        raw_iin = (user.iin or "").strip()
        if re.fullmatch(r"\d{12}", raw_iin):
            protected = protect_identifier(raw_iin)
            user.iin_hash = protected["hash"]
            user.iin_masked = protected["masked"]
            user.iin_encrypted = protected["encrypted"]
        raw_phone = user.phone or ""
        if raw_phone:
            phone = protect_phone(raw_phone)
            user.phone_encrypted = phone["encrypted"]
            user.phone_masked = phone["masked"]
        user.save()


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="iin_hash",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="iin_masked",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="user",
            name="iin_encrypted",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="phone_encrypted",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="phone_masked",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.RunPython(protect_existing_users, noop_reverse),
        migrations.RemoveField(model_name="user", name="iin"),
        migrations.RemoveField(model_name="user", name="phone"),
    ]
