from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("user_id", models.IntegerField(unique=True)),
                ("full_name", models.CharField(blank=True, max_length=255)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("role", models.CharField(blank=True, max_length=16)),
                ("bio", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=128)),
                ("phone", models.CharField(blank=True, max_length=32)),
                ("avatar", models.ImageField(blank=True, null=True, upload_to="profiles/")),
                ("is_public_phone", models.BooleanField(default=False)),
                ("is_public_email", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "profile_profile"},
        ),
    ]
