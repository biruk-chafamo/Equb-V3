# Generated by Django 5.0.4 on 2024-08-14 03:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moneypool', '0028_balancemanager_current_round_start_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentconfirmationrequest',
            name='message',
            field=models.TextField(blank=True),
        ),
    ]