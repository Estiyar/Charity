from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FundraisingCard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("author_id", models.IntegerField(db_index=True)),
                ("author_email", models.EmailField(blank=True, max_length=254)),
                ("author_full_name", models.CharField(blank=True, max_length=255)),
                ("full_name", models.CharField(max_length=255)),
                ("diagnosis", models.CharField(max_length=255)),
                ("city", models.CharField(max_length=128)),
                ("clinic", models.CharField(blank=True, max_length=255)),
                ("age", models.PositiveIntegerField(blank=True, null=True)),
                ("gender", models.CharField(blank=True, max_length=8)),
                ("description", models.TextField(blank=True)),
                ("photo_url", models.ImageField(blank=True, null=True, upload_to="cards/photos/")),
                ("target_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("collected_amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("end_date", models.DateField()),
                ("status", models.CharField(default="draft", max_length=32)),
                ("iin_encrypted", models.CharField(blank=True, max_length=64)),
                ("iin_masked", models.CharField(blank=True, max_length=32)),
                ("document_number_encrypted", models.CharField(blank=True, max_length=64)),
                ("document_number_masked", models.CharField(blank=True, max_length=32)),
                ("contact_phone", models.CharField(blank=True, max_length=32)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("moderator_comment", models.TextField(blank=True)),
                ("recipient_iin", models.CharField(blank=True, max_length=12)),
                ("is_self", models.BooleanField(default=False)),
                ("needs_extra_review", models.BooleanField(default=False)),
                ("escrow_spent", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("escrow_pending", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "cards_fundraisingcard", "ordering": ["-created_at"]},
        ),
    ]
