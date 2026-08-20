from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0004_collection_receipt"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="fundraisingcard",
            index=models.Index(fields=["status"], name="cards_status_idx"),
        ),
        migrations.AddIndex(
            model_name="fundraisingcard",
            index=models.Index(fields=["city"], name="cards_city_idx"),
        ),
        migrations.AddIndex(
            model_name="fundraisingcard",
            index=models.Index(fields=["diagnosis"], name="cards_diagnosis_idx"),
        ),
        migrations.AddIndex(
            model_name="fundraisingcard",
            index=models.Index(fields=["age"], name="cards_age_idx"),
        ),
        migrations.AddIndex(
            model_name="fundraisingcard",
            index=models.Index(fields=["target_amount"], name="cards_target_amount_idx"),
        ),
        migrations.AddIndex(
            model_name="fundraisingcard",
            index=models.Index(fields=["collected_amount"], name="cards_collected_idx"),
        ),
        migrations.AddIndex(
            model_name="fundraisingcard",
            index=models.Index(fields=["end_date"], name="cards_end_date_idx"),
        ),
        migrations.AddIndex(
            model_name="fundraisingcard",
            index=models.Index(fields=["status", "end_date"], name="cards_status_end_idx"),
        ),
    ]
