from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cards", "0008_moderator_comments"),
    ]

    operations = [
        migrations.AddField(
            model_name="fundraisingcard",
            name="report_risk_score",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="status_before_suspend",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="suspend_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="fundraisingcard",
            name="unique_report_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
