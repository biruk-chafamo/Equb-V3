# Generated by Django 5.0.4 on 2024-08-15 20:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moneypool', '0033_alter_paymentconfirmationrequest_equb_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentconfirmationrequest',
            name='equb',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_%(class)ss', to='moneypool.equb'),
        ),
    ]
