from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("moderation", "0002_initial"),
    ]

    operations = [
        migrations.DeleteModel(
            name="RedistributionDecision",
        ),
    ]
