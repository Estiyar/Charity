import re

from django.db import migrations, models


def protect_existing_records(apps, schema_editor):
    from ekomek_common.crypto import protect_identifier

    MedicalRecord = apps.get_model("verification", "MedicalRecord")
    FraudProfile = apps.get_model("verification", "FraudProfile")
    for record in MedicalRecord.objects.all():
        raw_iin = (record.iin or "").strip()
        if re.fullmatch(r"\d{12}", raw_iin):
            protected = protect_identifier(raw_iin)
            record.iin_hash = protected["hash"]
            record.iin_masked = protected["masked"]
            record.save()
    for profile in FraudProfile.objects.all():
        raw_iin = (profile.iin or "").strip()
        if re.fullmatch(r"\d{12}", raw_iin):
            protected = protect_identifier(raw_iin)
            profile.iin_hash = protected["hash"]
            profile.iin_masked = protected["masked"]
            profile.save()


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("verification", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicalrecord",
            name="iin_hash",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="medicalrecord",
            name="iin_masked",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="fraudprofile",
            name="iin_hash",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="fraudprofile",
            name="iin_masked",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.RunPython(protect_existing_records, noop_reverse),
        migrations.RemoveField(model_name="medicalrecord", name="iin"),
        migrations.RemoveField(model_name="fraudprofile", name="iin"),
        migrations.AlterField(
            model_name="medicalrecord",
            name="iin_hash",
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name="fraudprofile",
            name="iin_hash",
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
