from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0028_subscription"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionorder",
            name="wfp_email",
            field=models.EmailField(blank=True, default="", max_length=254, verbose_name="Email (WayForPay)"),
        ),
        migrations.AddField(
            model_name="subscriptionorder",
            name="wfp_phone",
            field=models.CharField(blank=True, default="", max_length=20, verbose_name="Телефон (WayForPay)"),
        ),
        migrations.AddField(
            model_name="subscriptionorder",
            name="wfp_name",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="Імʼя (WayForPay)"),
        ),
    ]
