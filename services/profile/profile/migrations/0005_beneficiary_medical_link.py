from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("profile", "0004_profile_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="beneficiary",
            name="medical_record_hash",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddIndex(
            model_name="representation",
            index=models.Index(fields=["verification_status"], name="profile_rep_verif_idx"),
        ),
    ]
