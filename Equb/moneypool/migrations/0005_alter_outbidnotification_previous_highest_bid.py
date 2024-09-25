# Generated by Django 5.0.4 on 2024-05-04 01:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moneypool', '0004_alter_equbinviterequest_equb_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='outbidnotification',
            name='previous_highest_bid',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='moneypool.bid'),
        ),
    ]