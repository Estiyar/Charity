from django.db import migrations, models


def protect_existing_phones(apps, schema_editor):
    from ekomek_common.crypto import protect_phone

    Profile = apps.get_model("profile", "Profile")
    for profile in Profile.objects.all():
        raw_phone = profile.phone or ""
        if raw_phone:
            protected = protect_phone(raw_phone)
            profile.phone_encrypted = protected["encrypted"]
            profile.phone_masked = protected["masked"]
            profile.save()


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("profile", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="phone_encrypted",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="phone_masked",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.RunPython(protect_existing_phones, noop_reverse),
        migrations.RemoveField(model_name="profile", name="phone"),
    ]
